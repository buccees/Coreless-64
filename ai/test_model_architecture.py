from ai.model_architecture import TransformerConfig, from_mapping


def test_native_transformer_config():
    config = TransformerConfig(64, 256, 4, 8, 1000, 512)
    assert config.hidden_size == 64
    assert config.num_heads == 8


def test_common_external_aliases_map_to_coreless():
    config = from_mapping({
        "d_model": 64,
        "ffn_dim": 256,
        "n_layer": 4,
        "n_head": 8,
        "vocab_size": 1000,
        "max_position_embeddings": 512,
    })
    assert config == TransformerConfig(64, 256, 4, 8, 1000, 512)


def test_invalid_head_dimension_fails():
    try:
        TransformerConfig(65, 256, 4, 8, 1000, 512)
    except ValueError:
        pass
    else:
        raise AssertionError("hidden size must divide evenly by head count")
