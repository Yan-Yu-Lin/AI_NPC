import pygame

class GameObject:
    def __init__(self, name, rect, interactions, description, state, thoughts):
        self.name = name
        self.rect = rect
        self.interactions = interactions
        self.description = description
        self.state = state
        self.thoughts = thoughts

class Player:
    def __init__(self, x, y, radius, speed):
        self.pos = [x, y]
        self.radius = radius
        self.speed = speed
        self.rect = pygame.Rect(x - radius, y - radius, radius * 2, radius * 2)

    def move(self, dx, dy):
        self.pos[0] += dx
        self.pos[1] += dy
        self.rect.topleft = (self.pos[0] - self.radius, self.pos[1] - self.radius)

class AI:
    def __init__(self, x, y, radius, speed):
        self.pos = [x, y]
        self.radius = radius
        self.speed = speed
        self.rect = pygame.Rect(x - radius, y - radius, radius * 2, radius * 2)
        self.target = None
        self.memory = []
        self.thought_queue = []
        self.decision_queue = []
        self.is_thinking = False
        self.thought_cache = {} 