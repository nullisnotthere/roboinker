"""
Constants for the Raspberry PI frontend GUI displayed on the TFT display.
"""

import pygame

WIN_WIDTH = 600
WIN_HEIGHT = 1024
WIN_SIZE = (WIN_WIDTH, WIN_HEIGHT)
WIN_RECT = pygame.Rect((0, 0), WIN_SIZE)

BG_COLOUR = pygame.Color("White")
FPS = 60

BASE_SCREEN_OFFSET = pygame.Vector2(200, 350)
DRAG_ARM_HITBOX_SIZE = 100  # Hitbox size in px for dragging arm

