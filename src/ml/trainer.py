from typing import List, Dict, Tuple
import pandas as pd
from src.ml.dataset import build_grouped_dataset
from src.ml.model import Lane7Ranker
from src.ml.features import get_feature_names

def train_lane7_model(
    features_list: List[Dict[str, float]], 
    labels: List[str], 
    canonical_ids: List[str],
    model_params: Dict = None
) -> Tuple[Lane7Ranker, pd.DataFrame, pd.Series, pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
    """
    End-to-end training pipeline.
    """
    print(f"Building dataset with {len(features_list)} pairs...")
    X_train, y_train, X_val, y_val, X_test, y_test = build_grouped_dataset(
        features_list, labels, canonical_ids, test_size=0.15, val_size=0.15
    )
    
    print(f"Train size: {len(X_train)}, Val size: {len(X_val)}, Test size: {len(X_test)}")
    
    ranker = Lane7Ranker(model_params=model_params)
    feature_names = get_feature_names()
    
    print("Training LightGBM model...")
    ranker.fit(X_train, y_train, X_val, y_val, feature_names=feature_names)
    print("Training complete.")
    
    return ranker, X_train, y_train, X_val, y_val, X_test, y_test
