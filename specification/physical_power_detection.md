# Coreless-64 physical power detection and auto-start hardware

## Status

**Required; physical implementation and validation pending.** The Python reference machine and virtual motherboard do not sense real voltage. This document defines the hardware boundary that must be implemented before Coreless can claim physical power-triggered startup.

## Signals and responsibilities

Use two distinct inputs to the startup controller:

- `POWER_PRESENT`: an electrically safe, appropriately isolated indication that the external input supply is connected and above its specified detection threshold.
- `POWER_GOOD`: a power-supervisor indication that every required low-voltage rail is within tolerance and has remained stable for its specified qualification interval.

`POWER_PRESENT` alone must never release reset or start the CPU. Startup is permitted only after `POWER_GOOD` is asserted and the detector/controller has completed debounce and sequencing. The detector must deassert power-good promptly when a monitored rail falls outside tolerance.

## Reference hardware architecture

1. **Input-supply presence detector:** use a purpose-built power monitor or comparator interface rated for the actual input voltage and transients. If the input is hazardous or mains-derived, use a certified isolated sensing stage; never connect mains or an unqualified divider directly to GPIO or low-voltage logic.
2. **Rail supervisor:** use a voltage supervisor / power-good IC matched to each required rail and its tolerance. For multiple rails, use a sequencer or combine supervisor outputs so every mandatory rail is valid before startup.
3. **Reset gate:** route the supervisor's valid output to the hardware reset/power-enable controller. Hold reset asserted during absent, unstable, brownout, or invalid power. Use the polarity and pull state required by the selected components.
4. **Startup controller:** after power-good is continuously valid for the selected qualification interval, emit one debounced `POWER_ON` event to the Coreless host/boot controller. Do not repeatedly reboot while power remains stable.
5. **Power-loss path:** on power-good deassertion, immediately inhibit new work and assert reset; where hold-up energy and hardware permit, signal orderly shutdown early enough to flush state. Never promise a graceful save after an abrupt loss without measured hold-up time and tested power-fail handling.
6. **Host interface:** expose power-present, power-good, reset, and fault state through defined electrical levels and documented connector pins. The digital Coreless identity/discovery protocol runs only after its host interface is powered and electrically ready.

## Required design inputs before choosing parts or resistor values

- External input supply type and nominal/minimum/maximum voltage.
- Every low-voltage rail, nominal voltage, tolerance, and startup order.
- Maximum input transient, reverse-polarity, and brownout conditions.
- Required detection threshold, assertion/deassertion delays, and reset polarity.
- Whether any input can be mains-referenced; required isolation class and safety certification.
- Available controller/host pins and electrical standards (for example, 3.3 V logic); never assume a GPIO is 5 V tolerant.
- Required shutdown behavior and measured energy/time available after a power-fail warning.

Do not select a divider ratio, pull-up, threshold, or specific component until these parameters are known. Any chosen component must be checked against its datasheet, input common-mode range, absolute maximum ratings, tolerance, temperature range, and fault behavior.

## Acceptance tests

- No power, undervoltage, brownout, or rail sequencing fault keeps reset asserted and prevents automatic boot.
- Power presence without all required rails valid does not start the machine.
- Valid, stable rails produce exactly one startup event and release reset in the specified order.
- Threshold hysteresis and qualification/debounce prevent chatter and repeated boot attempts around the threshold.
- Loss of any required rail deasserts `POWER_GOOD` and asserts reset within the supervisor's documented limits.
- Power-fail warning, hold-up interval, and persistent-state flush are measured under representative load; abrupt removal is tested separately.
- Input faults (open wire, short, reversed input, transient, supervisor disconnected) fail to a safe no-boot state.
- Test both the circuit on a bench and the integrated host/boot path. Software-only simulated tests are supplementary and cannot pass the physical validation gate.

## Safety boundary

This is a low-voltage architecture description, not a finished schematic or build authorization. Do not probe or wire mains directly. If the system is powered from mains, use a certified isolated AC/DC supply and an appropriately rated isolated detection circuit designed and reviewed for that application. Physical construction and measurements must be performed with suitable equipment and electrical-safety practices.

## Integration with Coreless software

The physical controller should report a normalized, timestamped power event to the host adapter. The host adapter must validate the event, confirm the selected persistent machine identity and boot target, then invoke the single canonical initialize → boot/resume → desktop attach lifecycle. The physical signal is an input to that lifecycle, not a second boot implementation.

Required event/state model: `ABSENT → PRESENT_UNQUALIFIED → POWER_GOOD → BOOTING → RUNNING`, with fault/power-loss transitions to `RESET_HELD` and safe recovery. Record fault cause and transition times for diagnostics. Physical power state and software machine state must be reported separately.


## Required USB operating modes

Coreless-64 must support two intended connection scenarios through a USB interface, without assuming the same cable provides both power and data:

1. **USB adapter / mobile standalone mode:** a compatible USB power adapter supplies the device. Detect input power, qualify all internal rails, then automatically boot the configured persistent Coreless identity. A power-only adapter does not provide a PC host, so local/standalone operation must not wait indefinitely for USB data enumeration.
2. **PC-connected mode:** a PC USB host supplies power when available and enumerates Coreless through a real USB device/data interface. After power-good, expose the configured device identity and capabilities, then attach the host I/O path. Power-present alone is not evidence that enumeration succeeded.

### USB design constraints

- Start with a **USB 5 V input baseline** unless the power budget later proves it insufficient. Do not assume a USB-C adapter provides 9 V, 12 V, or another USB-PD voltage without a correctly designed PD sink/controller and negotiated contract.
- Use a data-capable USB connector and a compliant device-side interface for PC connection. A charge-only cable/adapter can power the device but cannot enumerate it.
- Treat USB input attach/presence, rail `POWER_GOOD`, and PC USB enumeration as three separate states/events.
- Prevent back-feeding power from one source into another. If the design allows an adapter and PC connection at the same time, specify and implement a protected power-path/ideal-diode or equivalent power mux; do not directly tie two VBUS sources together.
- Define current budget and startup inrush against the actual adapter/PC-port limits. Keep loads gated until the input source's permitted current and all local rails are valid.
- If the device later needs more than the agreed 5 V USB input budget, choose a documented USB-PD sink design and verify voltage/current negotiation and fallback behavior. Battery operation is not implied by "mobile"; an internal battery and charging circuit would be a separate requirement.

### USB mode acceptance tests

- USB adapter with no data host: power-good qualifies and the selected persistent machine boots automatically.
- PC USB port: power-good qualifies, the device enumerates with the configured identity, and the host communication path attaches.
- Data-capable PC cable versus charge-only cable: power behavior is reported accurately; only the data-capable path is expected to enumerate.
- Power-only adapter does not produce a false enumeration-success status.
- Connecting/disconnecting the PC data path does not corrupt persistent state or cause repeated boot while power remains stable.
- Simultaneous or switched sources cannot back-feed each other; source transitions, current limits, and brownouts fail safely.
- Physical bench validation is required; virtual tests can validate the event/state contract but cannot establish USB electrical compliance.

## Shortest-path communication requirement

Treat directness as a system-wide architecture requirement, subject to safety, correctness, and observable failure handling. Prefer the shortest path that preserves the interface contract; do not add a broker, network hop, duplicate state store, polling loop, or extra serialization layer when a direct signal, shared-memory interface, or native bus endpoint is sufficient.

- **Power detection to reset control:** use a direct hardware supervisor/reset path. Do not make safe reset release depend on a desktop process, USB enumeration, or periodic software polling.
- **Power-good to startup:** hardware readiness gates reset; once the controller reports a stable ready event, software routes it into the one canonical machine lifecycle. Debounce/sequence in the controller, not through repeated host polling.
- **USB data path:** route the USB device controller to the Coreless host-interface/transport adapter through the minimum required driver and protocol layers. USB enumeration and identity validation remain explicit; do not invent direct USB device support until target hardware and controller are selected.
- **Internal components:** prefer direct calls for in-process operations, shared memory or a local IPC primitive for same-host isolation needs, and a native bus for physical peripherals. Use network transport only when the endpoints are actually remote or the interface requires it.
- **State ownership:** keep one canonical owner for machine, power, GPIO, and desktop-visible state. Observers subscribe/read from that owner rather than maintaining divergent shadow state.
- **Traceability:** document each hop in the communication path, why it exists, and its expected latency/error behavior. Measure end-to-end latency before optimizing; shortest hop count is a design preference, not proof of lowest latency.
- **Safety boundary:** never bypass voltage supervision, reset gating, electrical protection, protocol validation, or required isolation to reduce path length.

Acceptance: architecture review lists the path for power event, boot request, USB enumeration, host command, GPIO/LED update, and desktop display update; unnecessary hops and duplicate state are removed where tests show equivalence; timing and failure tests confirm no correctness regression.
