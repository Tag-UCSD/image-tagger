"""
Semantic segmentation for architectural regions.

Uses SegFormer-B5 fine-tuned on ADE20K (150 classes) to identify
architectural elements: walls, ceiling, floor, windows, doors, furniture.

Configuration
-------------
Install torch and transformers:
    pip install torch transformers

The model downloads automatically on first use (~400MB).

If dependencies are missing, falls back to MockSegmentationAnalyzer
which provides geometric approximations for testing.

Reference:
    Xie, E., et al. (2021). SegFormer: Simple and Efficient Design for 
    Semantic Segmentation with Transformers. NeurIPS.
"""

from __future__ import annotations

import logging
import os
from typing import Dict, Optional, TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from backend.science.core import AnalysisFrame

logger = logging.getLogger(__name__)

# Lazy imports for optional dependencies
_torch = None
_transformers = None
_MODELS_LOADED = False


def _load_dependencies():
    """Lazily load torch and transformers."""
    global _torch, _transformers, _MODELS_LOADED
    if _MODELS_LOADED:
        return _torch is not None
    
    _MODELS_LOADED = True
    try:
        import torch
        import transformers
        _torch = torch
        _transformers = transformers
        return True
    except ImportError:
        logger.warning(
            "SegmentationAnalyzer: torch/transformers not available. "
            "Install with: pip install torch transformers"
        )
        return False


# ADE20K class mapping - architecturally relevant subset
ADE20K_CLASSES = {
    0: 'wall', 1: 'building', 2: 'sky', 3: 'floor', 4: 'tree',
    5: 'ceiling', 6: 'road', 7: 'bed', 8: 'windowpane', 9: 'grass',
    10: 'cabinet', 14: 'door', 15: 'table', 18: 'curtain', 19: 'chair',
    22: 'painting', 23: 'sofa', 24: 'shelf', 27: 'mirror', 28: 'rug',
    36: 'lamp', 42: 'column', 49: 'fireplace', 53: 'stairs',
    62: 'bookcase', 65: 'toilet', 70: 'countertop', 71: 'stove',
    85: 'chandelier', 134: 'sconce',
}

# Map ADE20K to our vocabulary
ADE20K_TO_VOCAB = {
    'wall': 'wall', 'ceiling': 'ceiling', 'floor': 'floor',
    'windowpane': 'window', 'door': 'door', 'column': 'column',
    'stairs': 'stairs', 'fireplace': 'fireplace',
    'chandelier': 'chandelier', 'sconce': 'sconce', 'lamp': 'lamp',
    'chair': 'chair', 'sofa': 'sofa', 'table': 'table',
    'bed': 'bed', 'cabinet': 'cabinet', 'shelf': 'shelf',
    'bookcase': 'bookshelf', 'painting': 'artwork', 'rug': 'rug',
    'curtain': 'curtain', 'mirror': 'mirror',
    'sky': 'view.exterior', 'tree': 'view.exterior', 'grass': 'view.exterior',
}


class SegmentationAnalyzer:
    """
    Semantic segmentation analyzer using SegFormer.
    
    Follows the same pattern as other analyzers (ColorAnalyzer, FractalAnalyzer).
    Populates frame.segmentation_masks with binary masks per region.
    """
    
    MODEL_ID = "nvidia/segformer-b5-finetuned-ade-640-640"
    
    _model = None
    _processor = None
    _device = None
    
    @classmethod
    def _ensure_model(cls) -> bool:
        """Lazily load the model on first use."""
        if cls._model is not None:
            return True
        
        if not _load_dependencies():
            return False
        
        try:
            cls._device = "cuda" if _torch.cuda.is_available() else "cpu"
            cls._processor = _transformers.SegformerImageProcessor.from_pretrained(cls.MODEL_ID)
            cls._model = _transformers.SegformerForSemanticSegmentation.from_pretrained(cls.MODEL_ID)
            cls._model.to(cls._device)
            cls._model.eval()
            logger.info(f"SegmentationAnalyzer: loaded model on {cls._device}")
            return True
        except Exception:
            logger.warning("SegmentationAnalyzer: failed to load model", exc_info=True)
            return False
    
    def analyze(self, frame: "AnalysisFrame") -> None:
        """
        Run semantic segmentation and populate frame with masks.
        
        Adds to frame:
            - segmentation_map: (H, W) class indices
            - segmentation_masks: Dict[str, np.ndarray] binary masks
            - segmentation_confidence: (H, W) confidence values
        """
        if not self._ensure_model():
            logger.warning("SegmentationAnalyzer: model not available, skipping")
            return
        
        if frame.original_image is None:
            return
        
        image = frame.original_image
        h, w = image.shape[:2]
        
        # Preprocess
        inputs = self._processor(images=image, return_tensors="pt")
        inputs = {k: v.to(self._device) for k, v in inputs.items()}
        
        # Inference
        with _torch.no_grad():
            outputs = self._model(**inputs)
        
        # Upsample to original size
        logits = outputs.logits
        upsampled = _torch.nn.functional.interpolate(
            logits, size=(h, w), mode='bilinear', align_corners=False
        )
        
        # Get predictions
        probs = _torch.softmax(upsampled, dim=1)
        confidence, predicted = probs.max(dim=1)
        
        seg_map = predicted[0].cpu().numpy().astype(np.uint8)
        conf_map = confidence[0].cpu().numpy().astype(np.float32)
        
        # Store raw outputs
        frame.segmentation_map = seg_map
        frame.segmentation_confidence = conf_map
        
        # Build vocabulary masks
        frame.segmentation_masks = self._build_masks(seg_map)
        
        # Add summary attributes
        self._add_coverage_attributes(frame)
    
    def _build_masks(self, seg_map: np.ndarray) -> Dict[str, np.ndarray]:
        """Convert segmentation map to vocabulary-aligned binary masks."""
        masks = {}
        
        for ade_idx, ade_name in ADE20K_CLASSES.items():
            vocab_name = ADE20K_TO_VOCAB.get(ade_name)
            if vocab_name is None:
                continue
            
            mask = seg_map == ade_idx
            if not mask.any():
                continue
            
            # Merge into existing mask (e.g., multiple furniture → chair)
            if vocab_name in masks:
                masks[vocab_name] = masks[vocab_name] | mask
            else:
                masks[vocab_name] = mask
        
        return masks
    
    def _add_coverage_attributes(self, frame: "AnalysisFrame") -> None:
        """Add region coverage attributes to frame."""
        masks = getattr(frame, 'segmentation_masks', {})
        total_pixels = frame.original_image.shape[0] * frame.original_image.shape[1]
        
        for region_name, mask in masks.items():
            coverage = float(mask.sum()) / total_pixels
            frame.add_attribute(f"region.{region_name}.coverage", coverage)
    
    def get_shell_masks(self, frame: "AnalysisFrame") -> Dict[str, np.ndarray]:
        """Get masks for primary architectural shell only."""
        masks = getattr(frame, 'segmentation_masks', {})
        shell_classes = ['ceiling', 'floor', 'wall', 'window', 'door']
        return {k: v for k, v in masks.items() if k in shell_classes}


class MockSegmentationAnalyzer:
    """
    Mock segmentation for testing without GPU/model dependencies.
    Generates geometric approximations based on image position.
    """
    
    def analyze(self, frame: "AnalysisFrame") -> None:
        """Generate mock segmentation based on image geometry."""
        if frame.original_image is None:
            return
        
        h, w = frame.original_image.shape[:2]
        seg_map = np.zeros((h, w), dtype=np.uint8)
        
        # Ceiling: top 25%
        seg_map[:h//4, :] = 5  # ceiling class
        
        # Floor: bottom 30%
        seg_map[int(h*0.7):, :] = 3  # floor class
        
        # Walls: middle region
        seg_map[h//4:int(h*0.7), :] = 0  # wall class
        
        # Window: center of wall region
        seg_map[h//3:h//2, w//3:2*w//3] = 8  # windowpane class
        
        frame.segmentation_map = seg_map
        frame.segmentation_confidence = np.ones((h, w), dtype=np.float32) * 0.9
        
        # Build masks
        frame.segmentation_masks = {
            'ceiling': seg_map == 5,
            'floor': seg_map == 3,
            'wall': seg_map == 0,
            'window': seg_map == 8,
        }
        
        # Add coverage attributes
        total_pixels = h * w
        for region_name, mask in frame.segmentation_masks.items():
            coverage = float(mask.sum()) / total_pixels
            frame.add_attribute(f"region.{region_name}.coverage", coverage)
    
    def get_shell_masks(self, frame: "AnalysisFrame") -> Dict[str, np.ndarray]:
        masks = getattr(frame, 'segmentation_masks', {})
        shell_classes = ['ceiling', 'floor', 'wall', 'window', 'door']
        return {k: v for k, v in masks.items() if k in shell_classes}
