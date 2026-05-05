"""
E5 dutch language embedding model loading.

With a lot of thanks to the hard work of the researchers at Antwerp University!

@misc{banar2025mtebnle5nlembeddingbenchmark,
      title={MTEB-NL and E5-NL: Embedding Benchmark and Models for Dutch},
      author={Nikolay Banar and Ehsan Lotfi and Jens Van Nooten and Cristina Arhiliuc and Marija Kliocaite and Walter Daelemans},
      year={2025},
      eprint={2509.12340},
      archivePrefix={arXiv},
      primaryClass={cs.CL},
      url={https://arxiv.org/abs/2509.12340},
}
"""

from sentence_transformers import SentenceTransformer


def _load_e5_model_cached() -> SentenceTransformer:
    """Loads the E5 model.

    Returns:
        SentenceTransformer: A model instance.

    Raises:
        RuntimeError: If model loading fails.
    """
    model = SentenceTransformer(
        "clips/e5-small-trm-nl",
        device="cpu",
        backend="onnx",
    )  # tried small model, 'base' relatively slow
    model.max_seq_length = 256
    return model
