"""
BaseRenderer - Abstract base class for all renderers

This provides the common interface and functionality for all renderer classes.
"""

from abc import ABC, abstractmethod
from typing import Any, Tuple, Optional
import pygame


class BaseRenderer(ABC):
    """
    Abstract base class for all renderer components.
    
    This class defines the common interface that all renderers must implement,
    ensuring consistency across different rendering components.
    """
    
    def __init__(self, screen: pygame.Surface, font: pygame.font.Font):
        """
        Initialize the base renderer.
        
        Args:
            screen: The pygame surface to render to
            font: The font to use for text rendering
        """
        self.screen = screen
        self.font = font
        self.data = None
        
    @abstractmethod
    def update(self, data: Any):
        """
        Update the renderer with new data.
        
        Args:
            data: The data to render (type depends on specific renderer)
        """
        pass
    
    @abstractmethod
    def render(self, scale: float, offset: Tuple[int, int]):
        """
        Render the component to the screen.
        
        Args:
            scale: The scale factor for rendering
            offset: The (x, y) offset for rendering
        """
        pass
    
    def world_to_screen(self, pos: Tuple[float, float], scale: float, 
                       offset: Tuple[int, int]) -> Tuple[int, int]:
        """
        Convert world coordinates to screen coordinates.
        
        Args:
            pos: World position (x, y)
            scale: Scale factor
            offset: Screen offset (x, y)
            
        Returns:
            Screen coordinates (x, y)
        """
        return (
            int(pos[0] * scale + offset[0]),
            int(pos[1] * scale + offset[1])
        )
    
    def scale_size(self, size: Tuple[float, float], scale: float) -> Tuple[int, int]:
        """
        Scale a size by the scale factor.
        
        Args:
            size: Original size (width, height)
            scale: Scale factor
            
        Returns:
            Scaled size (width, height)
        """
        return (
            int(size[0] * scale),
            int(size[1] * scale)
        )
    
    def draw_text(self, text: str, pos: Tuple[int, int], 
                  color: Tuple[int, int, int] = (255, 255, 255),
                  background: Optional[Tuple[int, int, int]] = None):
        """
        Draw text at the specified position.
        
        Args:
            text: Text to draw
            pos: Screen position (x, y)
            color: Text color (r, g, b)
            background: Optional background color (r, g, b)
        """
        text_surface = self.font.render(text, True, color)
        
        if background:
            # Draw background rectangle
            text_rect = text_surface.get_rect()
            text_rect.topleft = pos
            padding = 5
            bg_rect = text_rect.inflate(padding * 2, padding * 2)
            pygame.draw.rect(self.screen, background, bg_rect)
        
        self.screen.blit(text_surface, pos)