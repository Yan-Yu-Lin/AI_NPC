"""
SpaceRenderer - Renders game spaces/rooms

This class is responsible for rendering the spatial layout of the game world,
including rooms, their connections, and labels.
"""

from typing import List, Tuple
import pygame

from interfaces import SpaceDisplayData
from .base_renderer import BaseRenderer


class SpaceRenderer(BaseRenderer):
    """
    Renderer for game spaces/rooms.
    
    This renderer draws:
    1. Space rectangles with borders
    2. Space names/labels
    3. Connections between spaces
    """
    
    def __init__(self, screen: pygame.Surface, font: pygame.font.Font):
        """
        Initialize the space renderer.
        
        Args:
            screen: The pygame surface to render to
            font: The font to use for space labels
        """
        super().__init__(screen, font)
        self.spaces: List[SpaceDisplayData] = []
        
        # Visual settings
        self.space_color = (100, 100, 100)
        self.space_border_color = (200, 200, 200)
        self.space_border_width = 2
        self.connection_color = (150, 150, 150)
        self.connection_width = 2
        self.label_color = (255, 255, 255)
        
    def update(self, spaces: List[SpaceDisplayData]):
        """
        Update the renderer with new space data.
        
        Args:
            spaces: List of space display data
        """
        self.spaces = spaces
    
    def render(self, scale: float, offset: Tuple[int, int]):
        """
        Render all spaces to the screen.
        
        Args:
            scale: The scale factor for rendering
            offset: The (x, y) offset for rendering
        """
        if not self.spaces:
            return
        
        # First pass: Draw connections (so they appear behind spaces)
        self._render_connections(scale, offset)
        
        # Second pass: Draw spaces
        for space in self.spaces:
            self._render_space(space, scale, offset)
    
    def _render_space(self, space: SpaceDisplayData, scale: float, 
                      offset: Tuple[int, int]):
        """
        Render a single space.
        
        Args:
            space: The space data to render
            scale: Scale factor
            offset: Screen offset
        """
        # Convert world coordinates to screen coordinates
        screen_pos = self.world_to_screen(space.position.to_tuple(), scale, offset)
        screen_size = self.scale_size(space.size.to_tuple(), scale)
        
        # Create rectangle
        rect = pygame.Rect(screen_pos[0], screen_pos[1], 
                          screen_size[0], screen_size[1])
        
        # Draw filled rectangle
        pygame.draw.rect(self.screen, self.space_color, rect)
        
        # Draw border
        pygame.draw.rect(self.screen, self.space_border_color, rect, 
                        self.space_border_width)
        
        # Draw space name
        self._render_space_label(space.name, rect)
    
    def _render_space_label(self, name: str, rect: pygame.Rect):
        """
        Render the space name label centered in the space.
        
        Args:
            name: Space name
            rect: Space rectangle
        """
        text_surface = self.font.render(name, True, self.label_color)
        text_rect = text_surface.get_rect()
        text_rect.center = rect.center
        self.screen.blit(text_surface, text_rect)
    
    def _render_connections(self, scale: float, offset: Tuple[int, int]):
        """
        Render connections between spaces.
        
        Args:
            scale: Scale factor
            offset: Screen offset
        """
        # Track drawn connections to avoid duplicates
        drawn_connections = set()
        
        for space in self.spaces:
            space_center = self._get_space_center(space, scale, offset)
            
            for connected_id in space.connected_space_ids:
                # Create a sorted tuple to avoid drawing the same connection twice
                connection_key = tuple(sorted([space.id, connected_id]))
                if connection_key in drawn_connections:
                    continue
                
                # Find the connected space
                connected_space = self._find_space_by_id(connected_id)
                if connected_space:
                    connected_center = self._get_space_center(connected_space, 
                                                            scale, offset)
                    
                    # Draw line between centers
                    pygame.draw.line(self.screen, self.connection_color,
                                   space_center, connected_center,
                                   self.connection_width)
                    
                    drawn_connections.add(connection_key)
    
    def _get_space_center(self, space: SpaceDisplayData, scale: float,
                         offset: Tuple[int, int]) -> Tuple[int, int]:
        """
        Get the screen center position of a space.
        
        Args:
            space: Space data
            scale: Scale factor
            offset: Screen offset
            
        Returns:
            Center position in screen coordinates
        """
        pos = self.world_to_screen(space.position.to_tuple(), scale, offset)
        size = self.scale_size(space.size.to_tuple(), scale)
        return (
            pos[0] + size[0] // 2,
            pos[1] + size[1] // 2
        )
    
    def _find_space_by_id(self, space_id: str) -> SpaceDisplayData:
        """
        Find a space by its ID.
        
        Args:
            space_id: The space ID to find
            
        Returns:
            The space data if found, None otherwise
        """
        for space in self.spaces:
            if space.id == space_id:
                return space
        return None