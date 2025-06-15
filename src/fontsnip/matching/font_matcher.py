# src/fontsnip/matching/font_matcher.py

"""
Handles the font matching process by comparing extracted features against a
pre-computed font database.

This module defines the FontMatcher class, which is responsible for the final
stage of the font identification workflow. It loads the serialized font
feature database created by the `build_font_database.py` script. Its primary
method takes the feature vectors extracted from a user's screen capture,
calculates an aggregate "target" vector, and then uses cosine similarity to
find the most similar fonts in the database.
"""

import pickle
import logging
from typing import List, Dict, Tuple, Optional

import numpy as np

# Set up a logger for this module
logger = logging.getLogger(__name__)


class FontMatcher:
    """
    Loads a pre-computed font feature database and finds the best font matches
    for a given set of feature vectors from a screen snip.
    """

    def __init__(self, database_path: str):
        """
        Initializes the FontMatcher and loads the font database from the given path.

        Args:
            database_path (str): The file path to the pickled font database
                                 (e.g., 'data/font_features.pkl').
        """
        self.font_database: Optional[Dict[str, np.ndarray]] = self._load_database(database_path)
        if not self.font_database:
            logger.error("Font database is empty or could not be loaded. Matching will not work.")
            # This allows the application to start even if the database is missing,
            # but matching attempts will fail gracefully.

    def _load_database(self, db_path: str) -> Optional[Dict[str, np.ndarray]]:
        """
        Loads the font feature database from a pickle file.

        Args:
            db_path (str): The path to the database file.

        Returns:
            A dictionary mapping font file names to their feature vectors,
            or None if loading fails.
        """
        try:
            with open(db_path, 'rb') as f:
                database = pickle.load(f)
                if not isinstance(database, dict) or not database:
                    logger.error(f"Database file at {db_path} is not a valid, non-empty dictionary.")
                    return None
                logger.info(f"Successfully loaded font database with {len(database)} fonts from {db_path}")
                return database
        except FileNotFoundError:
            logger.error(f"Font database file not found at: {db_path}. "
                         f"Please run the 'scripts/build_font_database.py' script.")
            return None
        except (pickle.UnpicklingError, EOFError) as e:
            logger.error(f"Error unpickling the font database file {db_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred while loading the font database: {e}")
            return None

    @staticmethod
    def _cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Calculates the cosine similarity between two non-zero vectors.

        Cosine similarity measures the cosine of the angle between two vectors,
        providing a measure of orientation similarity, independent of magnitude.

        Args:
            vec1 (np.ndarray): The first vector.
            vec2 (np.ndarray): The second vector.

        Returns:
            The cosine similarity score (from -1.0 to 1.0, where 1.0 is identical).
        """
        dot_product = np.dot(vec1, vec2)
        norm_vec1 = np.linalg.norm(vec1)
        norm_vec2 = np.linalg.norm(vec2)

        # Avoid division by zero if either vector is all zeros
        if norm_vec1 == 0 or norm_vec2 == 0:
            return 0.0

        return dot_product / (norm_vec1 * norm_vec2)

    def find_best_matches(self, snip_feature_vectors: List[np.ndarray], top_n: int = 3) -> List[Tuple[str, float]]:
        """
        Finds the top N best font matches for the given snip features.

        It computes an average feature vector from the snip, then compares this
        target vector against all fonts in the database using cosine similarity.

        Args:
            snip_feature_vectors (List[np.ndarray]): A list of feature vectors,
                one for each character recognized in the snip.
            top_n (int): The number of top matches to return.

        Returns:
            A list of tuples, where each tuple contains a font name (str) and its
            similarity score (float), sorted in descending order of similarity.
            Returns an empty list if no matches can be found or if input is invalid.
        """
        if not self.font_database:
            logger.warning("Cannot find matches; font database is not loaded.")
            return []

        if not snip_feature_vectors:
            logger.warning("Received an empty list of feature vectors. Cannot perform matching.")
            return []

        # 1. Average the feature vectors from the snip to get a single target vector.
        #    This represents the overall style of the font in the snip.
        try:
            target_vector = np.mean(snip_feature_vectors, axis=0)
        except (ValueError, np.AxisError) as e:
            logger.error(f"Error averaging feature vectors: {e}. Check if vectors have consistent dimensions.")
            return []

        # 2. Calculate the similarity between the target vector and each font in the database.
        scores = []
        for font_name, db_vector in self.font_database.items():
            # Defensive check: ensure vectors have the same dimension before comparison.
            # This prevents crashes if the database and feature extractor get out of sync.
            if target_vector.shape != db_vector.shape:
                logger.warning(
                    f"Shape mismatch between target vector {target_vector.shape} and "
                    f"database vector for '{font_name}' {db_vector.shape}. Skipping."
                )
                continue

            similarity = self._cosine_similarity(target_vector, db_vector)
            scores.append((font_name, similarity))

        if not scores:
            logger.warning("No valid comparisons could be made against the font database.")
            return []

        # 3. Sort the fonts by similarity score in descending order.
        scores.sort(key=lambda item: item[1], reverse=True)

        # 4. Return the top N results.
        return scores[:top_n]

```