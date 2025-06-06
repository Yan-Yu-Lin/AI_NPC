"""
NPCRenderer - Renders NPCs and their visual elements

This class is responsible for rendering NPCs, their states, and chat bubbles.
"""

from typing import List, Tuple, Optional
import pygame
import math

from interfaces import NPCDisplayData, NPCState
from .base_renderer import BaseRenderer


class NPCRenderer(BaseRenderer):
    """
    Renderer for NPCs and their visual elements.
    
    This renderer draws:
    1. NPC circles with colors based on state
    2. NPC names
    3. Chat bubbles for active NPCs
    4. Thinking indicators
    """
    
    def __init__(self, screen: pygame.Surface, font: pygame.font.Font):
        """
        Initialize the NPC renderer.
        
        Args:
            screen: The pygame surface to render to
            font: The font to use for NPC names and chat
        """
        super().__init__(screen, font)
        self.npcs: List[NPCDisplayData] = []
        self.active_npc_id: Optional[str] = None
        
        # Visual settings
        self.npc_radius = 15
        self.npc_colors = {
            NPCState.IDLE: (0, 200, 0),      # Green
            NPCState.THINKING: (255, 255, 0), # Yellow
            NPCState.TALKING: (0, 100, 255), # Blue
            NPCState.MOVING: (200, 100, 0),  # Orange
        }
        self.active_npc_color = (255, 0, 0)  # Red for active NPC
        self.name_color = (255, 255, 255)
        self.chat_bubble_color = (50, 50, 50)
        self.chat_text_color = (255, 255, 255)
        self.thinking_animation_speed = 2
        
    def update(self, npcs: List[NPCDisplayData], active_npc_id: Optional[str]):
        """
        Update the renderer with new NPC data.
        
        Args:
            npcs: List of NPC display data
            active_npc_id: ID of the currently active NPC
        """
        self.npcs = npcs
        self.active_npc_id = active_npc_id
    
    def render(self, scale: float, offset: Tuple[int, int]):
        """
        Render all NPCs to the screen.
        
        Args:
            scale: The scale factor for rendering
            offset: The (x, y) offset for rendering
        """
        if not self.npcs:
            return
        
        for npc in self.npcs:
            self._render_npc(npc, scale, offset)
            
            # Render chat bubble for active NPC with recent message
            if npc.id == self.active_npc_id and npc.last_message:
                self._render_chat_bubble(npc, scale, offset)
    
    def _render_npc(self, npc: NPCDisplayData, scale: float, 
                    offset: Tuple[int, int]):
        """
        Render a single NPC.
        
        Args:
            npc: The NPC data to render
            scale: Scale factor
            offset: Screen offset
        """
        # Convert world coordinates to screen coordinates
        screen_pos = self.world_to_screen(npc.position.to_tuple(), scale, offset)
        scaled_radius = int(self.npc_radius * scale)
        
        # Determine color based on state and active status
        if npc.id == self.active_npc_id:
            color = self.active_npc_color
        else:
            color = self.npc_colors.get(npc.state, (100, 100, 100))
        
        # Draw NPC circle
        pygame.draw.circle(self.screen, color, screen_pos, scaled_radius)
        
        # Draw border for better visibility
        pygame.draw.circle(self.screen, (255, 255, 255), screen_pos, 
                          scaled_radius, 2)
        
        # Draw thinking indicator if thinking
        if npc.state == NPCState.THINKING:
            self._render_thinking_indicator(screen_pos, scaled_radius)
        
        # Draw NPC name below
        self._render_npc_name(npc.name, screen_pos, scaled_radius)
    
    def _render_npc_name(self, name: str, pos: Tuple[int, int], radius: int):
        """
        Render the NPC name below the NPC circle.
        
        Args:
            name: NPC name
            pos: NPC center position
            radius: NPC radius
        """
        text_surface = self.font.render(name, True, self.name_color)
        text_rect = text_surface.get_rect()
        text_rect.centerx = pos[0]
        text_rect.top = pos[1] + radius + 5
        self.screen.blit(text_surface, text_rect)
    
    def _render_thinking_indicator(self, pos: Tuple[int, int], radius: int):
        """
        Render animated thinking dots above the NPC.
        
        Args:
            pos: NPC center position
            radius: NPC radius
        """
        # Create animated dots
        time = pygame.time.get_ticks() / 500  # Slow down animation
        dot_count = 3
        dot_radius = 3
        spacing = 8
        
        for i in range(dot_count):
            # Calculate dot position
            x = pos[0] - (dot_count - 1) * spacing // 2 + i * spacing
            y = pos[1] - radius - 15
            
            # Animate opacity
            opacity = int(128 + 127 * math.sin(time + i * 0.5))
            color = (opacity, opacity, opacity)
            
            pygame.draw.circle(self.screen, color, (x, y), dot_radius)
    
    def _render_chat_bubble(self, npc: NPCDisplayData, scale: float,
                           offset: Tuple[int, int]):
        """
        Render a chat bubble for the NPC's last message.
        
        Args:
            npc: The NPC data
            scale: Scale factor
            offset: Screen offset
        """
        if not npc.last_message:
            return
        
        # Convert position
        screen_pos = self.world_to_screen(npc.position.to_tuple(), scale, offset)
        scaled_radius = int(self.npc_radius * scale)
        
        # Prepare text
        max_width = 200
        lines = self._wrap_text(npc.last_message, max_width)
        
        # Calculate bubble size
        line_height = self.font.get_linesize()
        padding = 10
        bubble_width = max_width + padding * 2
        bubble_height = len(lines) * line_height + padding * 2
        
        # Position bubble above NPC
        bubble_x = screen_pos[0] - bubble_width // 2
        bubble_y = screen_pos[1] - scaled_radius - bubble_height - 20
        
        # Draw bubble background
        bubble_rect = pygame.Rect(bubble_x, bubble_y, bubble_width, bubble_height)
        pygame.draw.rect(self.screen, self.chat_bubble_color, bubble_rect, 
                        border_radius=10)
        pygame.draw.rect(self.screen, (255, 255, 255), bubble_rect, 2, 
                        border_radius=10)
        
        # Draw bubble tail
        tail_points = [
            (screen_pos[0], bubble_y + bubble_height),
            (screen_pos[0] - 10, bubble_y + bubble_height - 5),
            (screen_pos[0] + 10, bubble_y + bubble_height - 5)
        ]
        pygame.draw.polygon(self.screen, self.chat_bubble_color, tail_points)
        
        # Draw text
        y = bubble_y + padding
        for line in lines:
            text_surface = self.font.render(line, True, self.chat_text_color)
            text_rect = text_surface.get_rect()
            text_rect.centerx = bubble_x + bubble_width // 2
            text_rect.top = y
            self.screen.blit(text_surface, text_rect)
            y += line_height
    
    def _wrap_text(self, text: str, max_width: int) -> List[str]:
        """
        Wrap text to fit within the specified width.
        
        Args:
            text: Text to wrap
            max_width: Maximum width in pixels
            
        Returns:
            List of wrapped lines
        """
        words = text.split(' ')
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            test_surface = self.font.render(test_line, True, (0, 0, 0))
            
            if test_surface.get_width() <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    # Word is too long, add it anyway
                    lines.append(word)
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines