try:
    from ._version import version as __version__
except ImportError:
    __version__ = 'unknown'


from ._widget import MainWidget, PredictionWidget, threshold_prob
from ._postprocess_widget import post_process_filters
from ._score_widget import compute_score
