"""
Person 1's component: Detection.

Public surface (synthetic path):

    from detection.dataset import SITE_CONFIGS, generate_all_sites, Consumer
    from detection.features import extract_all, to_anomaly_record
    from detection.detector import SiteDetector
    from detection.baseline import evaluate_detection
    from detection.pooled_recheck import build_pattern_index, recheck_against_pool

Public surface (real SGCC data path — see detection/README.md, "The
real-data path," for why this is parallel rather than a drop-in
replacement):

    from detection.real_dataset import load_real_sgcc, RealConsumer
    from detection.real_detector import SupervisedSiteDetector
    from detection.real_pipeline import run_real_pipeline

See detection/README.md for the full task list and interface contract with
Person 2 (policy/) and Person 3 (orchestration/).
"""

from .baseline import DetectionMetrics, evaluate_detection
from .dataset import SITE_CONFIGS, Consumer, SiteConfig, generate_all_sites, generate_site
from .detector import FlaggedAnomaly, SiteDetector, fit_and_flag
from .drift import DRIFT_DURATION_THRESHOLD, DRIFT_MAGNITUDE_THRESHOLD, clears_drift, filter_for_sharing
from .features import ConsumerFeatures, extract_all, extract_ml_features, extract_shape_features, to_anomaly_record
from .pooled_recheck import build_pattern_index, recheck_against_pool
from .real_dataset import RealConsumer, RealDatasetError, load_real_sgcc
from .real_detector import SupervisedFlag, SupervisedSiteDetector
from .real_features import clears_real_drift, real_ml_feature_vector, real_shape_descriptor
from .real_pipeline import RealPipelineResult, run_real_pipeline

__all__ = [
    "SITE_CONFIGS",
    "Consumer",
    "SiteConfig",
    "generate_all_sites",
    "generate_site",
    "SiteDetector",
    "FlaggedAnomaly",
    "fit_and_flag",
    "DRIFT_MAGNITUDE_THRESHOLD",
    "DRIFT_DURATION_THRESHOLD",
    "clears_drift",
    "filter_for_sharing",
    "ConsumerFeatures",
    "extract_all",
    "extract_ml_features",
    "extract_shape_features",
    "to_anomaly_record",
    "DetectionMetrics",
    "evaluate_detection",
    "build_pattern_index",
    "recheck_against_pool",
    "RealConsumer",
    "RealDatasetError",
    "load_real_sgcc",
    "SupervisedFlag",
    "SupervisedSiteDetector",
    "clears_real_drift",
    "real_ml_feature_vector",
    "real_shape_descriptor",
    "RealPipelineResult",
    "run_real_pipeline",
]
