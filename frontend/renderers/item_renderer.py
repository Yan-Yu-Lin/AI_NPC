"""
ItemRenderer - Renders items in the game world

This class is responsible for rendering items with their images or representations.
"""

from typing import List, Tuple, Dict, Optional
import pygame
import os

from interfaces import ItemDisplayData
from .base_renderer import BaseRenderer


class ItemRenderer(BaseRenderer):
    """
    Renderer for game items.
    
    This renderer draws:
    1. Item images (if available)
    2. Fallback item representations
    3. Item names
    """
    
    def __init__(self, screen: pygame.Surface, font: pygame.font.Font):
        """
        Initialize the item renderer.
        
        Args:
            screen: The pygame surface to render to
            font: The font to use for item labels
        """
        super().__init__(screen, font)
        self.items: List[ItemDisplayData] = []
        self.item_images: Dict[str, pygame.Surface] = {}
        self.image_cache: Dict[str, pygame.Surface] = {}
        
        # Visual settings
        self.default_item_size = (30, 30)
        self.default_item_color = (200, 150, 50)  # Gold color
        self.item_border_color = (255, 255, 255)
        self.label_color = (255, 255, 255)
        self.label_background = (0, 0, 0, 128)  # Semi-transparent black
        
        # Load item images
        self._load_item_images()
    
    def update(self, items: List[ItemDisplayData]):
        """
        Update the renderer with new item data.
        
        Args:
            items: List of item display data
        """
        self.items = items
    
    def render(self, scale: float, offset: Tuple[int, int]):
        """
        Render all items to the screen.
        
        Args:
            scale: The scale factor for rendering
            offset: The (x, y) offset for rendering
        """
        if not self.items:
            return
        
        for item in self.items:
            self._render_item(item, scale, offset)
    
    def _render_item(self, item: ItemDisplayData, scale: float,
                     offset: Tuple[int, int]):
        """
        Render a single item.
        
        Args:
            item: The item data to render
            scale: Scale factor
            offset: Screen offset
        """
        # Convert world coordinates to screen coordinates
        screen_pos = self.world_to_screen(item.position.to_tuple(), scale, offset)
        
        # Determine item size
        if item.size:
            item_size = self.scale_size(item.size.to_tuple(), scale)
        else:
            item_size = self.scale_size(self.default_item_size, scale)
        
        # Try to render with image first
        if not self._render_item_image(item, screen_pos, item_size):
            # Fallback to simple rectangle
            self._render_item_fallback(item, screen_pos, item_size)
        
        # Render item name below
        self._render_item_label(item.name, screen_pos, item_size)
    
    def _render_item_image(self, item: ItemDisplayData, pos: Tuple[int, int],
                          size: Tuple[int, int]) -> bool:
        """
        Try to render item with an image.
        
        Args:
            item: Item data
            pos: Screen position
            size: Item size
            
        Returns:
            True if image was rendered, False otherwise
        """
        # Check if we have an image for this item
        image_key = item.image_path or item.name.lower()
        
        if image_key in self.item_images:
            # Get cached scaled image or create new one
            cache_key = f"{image_key}_{size[0]}x{size[1]}"
            
            if cache_key not in self.image_cache:
                # Scale image to fit size
                original = self.item_images[image_key]
                scaled = pygame.transform.scale(original, size)
                self.image_cache[cache_key] = scaled
            
            # Draw the image
            image = self.image_cache[cache_key]
            image_rect = image.get_rect()
            image_rect.center = (pos[0] + size[0] // 2, pos[1] + size[1] // 2)
            self.screen.blit(image, image_rect)
            
            return True
        
        return False
    
    def _render_item_fallback(self, item: ItemDisplayData, pos: Tuple[int, int],
                             size: Tuple[int, int]):
        """
        Render item as a simple shape when no image is available.
        
        Args:
            item: Item data
            pos: Screen position
            size: Item size
        """
        # Create rectangle
        rect = pygame.Rect(pos[0], pos[1], size[0], size[1])
        
        # Use item color if specified, otherwise default
        color = self.default_item_color
        if hasattr(item, 'color') and item.color:
            color = item.color
        
        # Draw filled rectangle
        pygame.draw.rect(self.screen, color, rect)
        
        # Draw border
        pygame.draw.rect(self.screen, self.item_border_color, rect, 2)
        
        # Draw a simple icon/symbol in the center
        center = rect.center
        # Draw a star shape as a generic item icon
        self._draw_star(center, min(size) // 3, (255, 255, 255))
    
    def _render_item_label(self, name: str, pos: Tuple[int, int],
                          size: Tuple[int, int]):
        """
        Render the item name below the item.
        
        Args:
            name: Item name
            pos: Item position
            size: Item size
        """
        # Create smaller font for item labels
        small_font = pygame.font.Font(self.font.get_name(), 
                                     int(self.font.get_height() * 0.7))
        
        text_surface = small_font.render(name, True, self.label_color)
        text_rect = text_surface.get_rect()
        text_rect.centerx = pos[0] + size[0] // 2
        text_rect.top = pos[1] + size[1] + 2
        
        # Draw semi-transparent background for better readability
        bg_rect = text_rect.inflate(4, 2)
        bg_surface = pygame.Surface((bg_rect.width, bg_rect.height))
        bg_surface.set_alpha(128)
        bg_surface.fill((0, 0, 0))
        self.screen.blit(bg_surface, bg_rect)
        
        # Draw text
        self.screen.blit(text_surface, text_rect)
    
    def _draw_star(self, center: Tuple[int, int], radius: int,
                   color: Tuple[int, int, int]):
        """
        Draw a simple star shape.
        
        Args:
            center: Center position
            radius: Star radius
            color: Star color
        """
        # Calculate star points
        points = []
        for i in range(10):
            angle = i * 36 * 3.14159 / 180
            if i % 2 == 0:
                r = radius
            else:
                r = radius * 0.5
            x = center[0] + r * pygame.math.Vector2(1, 0).rotate(angle * 180 / 3.14159).x
            y = center[1] + r * pygame.math.Vector2(1, 0).rotate(angle * 180 / 3.14159).y
            points.append((x, y))
        
        pygame.draw.polygon(self.screen, color, points)
    
    def _load_item_images(self):
        """Load item images from the file system."""
        image_dir = "worlds/picture"
        
        if not os.path.exists(image_dir):
            return
        
        # Map item names to image files
        image_mappings = {
            "bed": "bed.png",
            "single_bed": "bed_single.png",
            "bookshelf": "bookshelf.png",
            "chair": "chair_black.png",
            "brown_chair": "chair_brown.png",
            "diary": "diary.png",
            "knife": "knife.png",
            "magazine": "magazine.png",
            "pen": "pen.png",
            "piano": "piano.png",
            "refrigerator": "refrigerator.png",
            "remote": "remote_control.png",
            "sofa": "sofa.png",
            "single_sofa": "single_sofa.png",
            "sink": "sink.png",
            "stool": "stool_gray.png",
            "white_stool": "stool_white.png",
            "table": "table.png",
            "white_table": "table_white.png",
            "toilet": "toilet.png",
            "bathtub": "bathtub.png"
        }
        
        for item_name, filename in image_mappings.items():
            filepath = os.path.join(image_dir, filename)
            if os.path.exists(filepath):
                try:
                    image = pygame.image.load(filepath)
                    self.item_images[item_name] = image
                except pygame.error as e:
                    print(f"Failed to load image {filepath}: {e}")