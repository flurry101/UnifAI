import pandas as pd
import numpy as np
from sklearn.model_selection import GroupShuffleSplit
from typing import Tuple, List, Dict, Any
from src.ml.features import get_feature_names

# The taxonomy classes we support
CLASSES = ["IDENTICAL", "EQUIVALENT", "VARIANT_OF", "DISTINCT", "UNDETERMINED"]

def map_label(relation: str) -> int:
    """Map string class label to integer."""
    if pd.isna(relation):
        return CLASSES.index("UNDETERMINED")
    if relation == "UNRELATED":
        relation = "DISTINCT"
    if relation in CLASSES:
        return CLASSES.index(relation)
    return CLASSES.index("UNDETERMINED")

def check_leakage(features_df: pd.DataFrame):
    """
    Ensure no target/leakage features are present in the feature matrix X.
    """
    banned_substrings = [
        "canonical", "relation", "status", "decision", 
        "ground_truth", "target", "score", "explanation", "class"
    ]
    for col in features_df.columns:
        for ban in banned_substrings:
            if ban in col.lower():
                raise ValueError(f"CRITICAL: Potential label leakage detected in feature column '{col}' (matched banned substring '{ban}').")

def build_grouped_dataset(
    features_list: List[Dict[str, float]], 
    labels: List[str], 
    canonical_ids: List[str],
    test_size: float = 0.2,
    val_size: float = 0.1,
    random_state: int = 42
) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
    """
    Constructs the train/val/test splits using GroupShuffleSplit on canonical_id.
    """
    df_x = pd.DataFrame(features_list)
    
    # 1. Check for Leakage
    check_leakage(df_x)
    
    # Verify we only have the correct feature columns
    expected_cols = get_feature_names()
    for col in df_x.columns:
        if col not in expected_cols:
            raise ValueError(f"CRITICAL: Unexpected feature '{col}' not in allowed feature list.")
            
    df_y = pd.Series([map_label(l) for l in labels], name="target")
    groups = pd.Series(canonical_ids, name="canonical_id")
    
    # First split: Train vs Temp (Val+Test)
    temp_size = test_size + val_size
    gss1 = GroupShuffleSplit(n_splits=1, test_size=temp_size, random_state=random_state)
    train_idx, temp_idx = next(gss1.split(df_x, df_y, groups=groups))
    
    X_train, y_train = df_x.iloc[train_idx], df_y.iloc[train_idx]
    X_temp, y_temp, groups_temp = df_x.iloc[temp_idx], df_y.iloc[temp_idx], groups.iloc[temp_idx]
    
    # Second split: Val vs Test
    # Calculate relative test size inside temp
    rel_test_size = test_size / temp_size
    gss2 = GroupShuffleSplit(n_splits=1, test_size=rel_test_size, random_state=random_state)
    val_idx, test_idx = next(gss2.split(X_temp, y_temp, groups=groups_temp))
    
    X_val, y_val = X_temp.iloc[val_idx], y_temp.iloc[val_idx]
    X_test, y_test = X_temp.iloc[test_idx], y_temp.iloc[test_idx]
    
    return X_train, y_train, X_val, y_val, X_test, y_test
