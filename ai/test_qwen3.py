from qwen3 import Qwen3Config


def test_qwen3_config_supports_gqa():
    cfg = Qwen3Config(5120, 17408, 64, 64, 8, 151936, 40960)
    assert cfg.resolved_head_dim == 80
    assert cfg.kv_group_size == 8


def test_qwen3_config_rejects_invalid_head_ratio():
    try:
        Qwen3Config(512, 1024, 2, 8, 3, 100, 128)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid GQA ratio was accepted")
