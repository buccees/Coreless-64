# Coreless-64 integrated motherboard and communication-path trace

**Status:** architecture trace based on the current working-branch source. This is not a schematic or proof of physical hardware operation.

## Design rule

Preserve the intended architecture: digital switches are the control/routing elements; the digital AI chipset is a programmable local control/dispatch component; Coreless owns machine execution and persistent state; external equipment provides power and host I/O. Prefer the shortest direct path that preserves safety, protocol validation, and one canonical owner for state.

## End-to-end path

```text
USB adapter / PC USB VBUS
        |
        v
Input protection + source selection / back-feed prevention
        |
        +----> POWER_PRESENT (presence only; not permission to run)
        |
        v
Rail regulation + per-rail voltage supervision
        |
        +----> POWER_GOOD ----> hardware reset gate
        |                           |
        |                           v
        |                    stable startup release
        |                           |
        v                           v
USB device controller/data interface <----> PC host enumeration + identity/capability exchange
        |                                      (only when a data host/cable exists)
        v
Host adapter / validated power-start event
        |
        v
ONE canonical CorelessSystem lifecycle
        |
        +--> CorelessMachine
        |      +--> CPU(s) + shared Coreless RAM
        |      +--> PersistentMachineImage / filesystem / device fabric
        |      +--> VirtualMotherboard (current reference netlist)
        |      +--> scheduler / work distributor / AI compute fabric
        |
        +--> CorelessOS + processes + desktop model
        |
        +--> Persistent AI runtime / AI registry
        |
        v
Canonical device/desktop state --> host display/input adapters
        |
        +--> direct motherboard digital-switch/control endpoints
        +--> status LED/GPIO state -> desktop status dot/menu
```

This diagram intentionally separates the electrical power path from the USB data path. A power-only adapter can boot standalone mode; it cannot perform PC enumeration. Hardware reset safety must work even when the USB host, OS, desktop, or AI is unavailable.

## Source trace: what exists today

### 1. Unified runtime and state ownership

- `reference/system.py` composes `CorelessMachine`, `CorelessOS`, `PersistentAIRuntime`, and the same motherboard instance owned by the machine.
- `CorelessMachine` in `reference/machine_runtime.py` owns the persistent machine image, CPUs, shared RAM, device fabric, filesystem, virtual motherboard, scheduler, work distributor, and `AIComputeFabric`.
- `CorelessSystem.motherboard` aliases `CorelessMachine.motherboard`; this is the correct single-owner pattern. Do not create a second motherboard or separate boot runtime.
- Machine/AI state is stored through the persistent image and AI runtime. Physical power status is not currently sensed or stored by the virtual netlist.

### 2. Current digital motherboard

- `reference/virtual_motherboard.py` currently defines logical VCC/GND rails, active-low reset, a modeled clock, IRQ, four GPIO paths, and digital peripheral models for status LED, activity LED, buzzer, and fault LED.
- `reference/circuit_simulator.py` resolves logical levels, pulls, high-impedance outputs, floating inputs, and conflicting digital drivers.
- This is a deterministic logical netlist; it does not simulate real voltage, current, transistor behavior, analog thresholds, power sequencing, or a physical switch IC.
- No separately named digital-switch controller or physical switch part is established by these files. The physical switch topology/pinout therefore remains an implementation contract, not a verified circuit.

### 3. Existing AI compute path

- `CorelessMachine` creates an `AIComputeFabric` and a machine scheduler.
- `CorelessSystem` restores `PersistentAIRuntime`, attaches its registry to the machine, and exposes AI compute/analysis entry points.
- Registered AI cores can be exposed to the scheduler as native Coreless resources; the scheduler/work distributor chooses a resource according to the declared capability and preference contract.
- This is the existing software AI path. No physical AI chip is assumed. The digital chipset is to be programmed as a first-class controller connected directly to the existing AI fabric/scheduler and the canonical virtual motherboard. The controller itself remains to be implemented.
- Keep AI as a local compute resource behind Coreless policy. Do not make it the authority for safe power detection, reset release, or electrical protection.

### 4. Host discovery and USB boundary

- `reference/host_discovery.py` validates identity frames and capability/channel advertisements from a provider.
- `reference/host_interface.py` handles identity, negotiation, attachment, and host I/O boundaries.
- `reference/host_transport.py` binds a validated endpoint to negotiated channels.
- `reference/linux_host_network.py` is a configured TLS/TCP bootstrap path, not physical USB enumeration.
- `specification/linux_host_platform.md` explicitly leaves the physical bus/endpoint selection open.
- No physical USB device controller, USB enumeration provider, or electrical power detector is demonstrated by this trace.

### 5. Desktop and GPIO status

- `reference/desktop_host.py` renders the top-right status dot and reads the desktop model's status-LED menu state. Its 250 ms refresh is UI rendering refresh, not the hardware power detector and not a reason to poll power-good in software.
- GPIO state should remain owned by the canonical motherboard/device state; the desktop is an observer/controller surface, not another machine or duplicate GPIO authority.

## Shortest-path decisions

| Path | Preferred design | Avoid |
|---|---|---|
| Input voltage -> safe reset | Protection, rail supervisors, direct hardware reset gate | AI/software polling or desktop-dependent reset |
| Power-good -> boot | One debounced ready event into the canonical lifecycle | Multiple competing boot entry points |
| PC USB -> identity/data | Native device controller and the minimum necessary validated driver/protocol layers | TCP loopback/network detour for a local USB link |
| AI chipset -> local compute | Direct supported local bus/control interface into the Coreless compute boundary | Routing local chip traffic through an external network or duplicate AI service |
| Digital switch -> controlled function | Named control signal, one state owner, direct resolved path | Shadow state in multiple managers |
| GPIO -> desktop status | Canonical GPIO/peripheral state observed by the desktop model | Independent fake LED state or a second motherboard |
| Components on the same machine | Direct call when in-process; shared memory/local IPC only when isolation requires it | Serialization/broker/network hops without a contract need |
| Independent Coreless components | Hub protocol at the actual component boundary | Forcing autonomous components through a single global in-process path |

Shortest hop count is a design target, not a latency measurement. Keep protocol validation, arbitration, required isolation, error reporting, and reset safety.

## Small improvements with low architectural risk

1. **Define one power event contract** with separate `POWER_PRESENT`, `POWER_GOOD`, `USB_ENUMERATED`, `BOOTING`, `RUNNING`, and `FAULT/RESET_HELD` states. Do not treat them as synonyms.
2. **Keep any future physical reset supervisor distinct from software controller reset:** this software chipset reset only clears controller state and does not release motherboard reset.
3. **Keep the current canonical object graph:** `CorelessSystem` -> its one `CorelessMachine` -> its one `VirtualMotherboard`; the AI registry/fabric is integrated into that machine, not instantiated as a parallel machine.
4. **Do not use TCP as a substitute for local USB:** retain TCP only for real network peers. Add a USB provider after selecting the physical USB device controller and wire protocol.
5. **Implement the digital AI chipset:** add a deterministic control/status interface to the canonical virtual motherboard and connect it directly to the existing AI fabric/scheduler. Follow `specification/ai_chipset_integration.md`; do not add a parallel runtime.\n6. **Keep physical-interface work explicitly separate:** connector/USB mode, current budget, regulated rails, supervisor thresholds, and physical switch truth tables remain future hardware requirements; they are not requirements for the digital AI controller.
7. **Verify boot/resume semantics before claiming automatic resume:** inspect how persistent machine state and OS state are restored and ensure a power-start event cannot accidentally create a second machine or overwrite the selected image.
8. **Measure the path after implementation:** trace event timestamps and latency across detector -> reset -> startup event -> boot -> USB enumeration -> first host I/O; optimize only demonstrated extra hops.

## Open design facts blocking pin-level implementation

- Digital chipset control/status behavior is implemented in `reference/digital_ai_chipset.py`; remaining work is broader integration verification and UI exposure, not inventing a physical AI-chip contract.
- Digital-switch inventory: which function each switch controls, signal polarity, default/fail-safe state, electrical rating, and whether it is a physical switch IC/transistor network or a logical switch in the digital model.
- USB connector/type and device-controller choice; USB 5 V input current budget and whether simultaneous PC/adapter power is allowed.
- Full internal rail list, tolerances, sequencing, brownout thresholds, and measured hold-up time.

## Acceptance evidence

- A code-level call/ownership map verifies that boot, machine, motherboard, AI registry/fabric, and desktop all reference the canonical runtime.
- State-machine tests show one startup event per stable power-on, no boot on invalid rails, and no false USB-enumerated state in adapter-only mode.
- Host tests validate identity and channels before attach and prove local USB does not take a network detour.
- Bench evidence validates power supervisors, reset timing, switch electrical behavior, AI chipset interface, USB enumeration, source switching, and power-loss behavior.
- Software tests and a green CI run must not be reported as physical validation.
