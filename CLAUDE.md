# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
This is an AI NPC (Non-Player Character) system that uses OpenAI's API to simulate intelligent NPCs in a game environment. The project is currently undergoing a major refactoring to separate frontend (Pygame display) and backend (AI logic) concerns.

## Running the Application
```bash
# Install dependencies
pip install -r requirements.txt

# Run the main application
python main.py

# Alternative entry points
python backend.py  # Run backend directly
python pygame_display.py  # Run display system
```

## Key Architecture Components

### Current Structure (Being Refactored)
- **backend.py**: AI NPC logic mixed with some display code (needs cleanup)
- **pygame_display.py**: 1013-line monolithic function handling all display logic (needs OOP refactor)
- **interfaces.py**: New API interface definitions for frontend-backend separation
- **backend_adapter.py**: Adapter pattern implementation for clean separation

### Refactoring Strategy (From PRD)
The project is being transformed from a monolithic structure to a clean MVC architecture:

1. **Backend Layer** (Pure AI Logic)
   - `AI_System`: Core AI processing without display code
   - `NPC`: Character logic and behavior
   - `WorldManager`: World state management
   - Remove all pygame/display imports from backend.py

2. **Frontend Layer** (Pygame Display)
   - Transform pygame_display.py into OOP classes:
     - `GameDisplay`: Main controller
     - `NPCRenderer`, `SpaceRenderer`, `ItemRenderer`: Rendering components
     - `UIManager`: UI components
     - `EventHandler`: Event management
     - `TerminalInterface`: Terminal commands

3. **Communication Layer**
   - All frontend-backend communication through interfaces.py
   - No direct cross-layer imports

## Task Master Integration
This project uses Task Master for task management through the MCP (Model Context Protocol) server. The refactoring tasks are tracked in `.taskmaster/`.

When using Task Master MCP tools, always provide the `projectRoot` parameter with the absolute project path.

### Common Task Master Operations (via MCP)
- **View all tasks**: Use `mcp__task-master__get_tasks` with projectRoot
- **Check next task**: Use `mcp__task-master__next_task` to find tasks with satisfied dependencies
- **Get task details**: Use `mcp__task-master__get_task` with task ID
- **Update task status**: Use `mcp__task-master__set_task_status` with id and status (pending/done/in-progress)
- **Analyze complexity**: Use `mcp__task-master__analyze_project_complexity` before breaking down tasks
- **Expand complex tasks**: Use `mcp__task-master__expand_task` to create subtasks
- **Add new tasks**: Use `mcp__task-master__add_task` with a prompt describing the task

### Task Management Workflow
1. Start by checking current tasks with `mcp__task-master__get_tasks`
2. Use `mcp__task-master__next_task` to identify what to work on
3. For complex tasks, run `mcp__task-master__analyze_project_complexity` first
4. Break down complex tasks with `mcp__task-master__expand_task`
5. Update task status as you progress with `mcp__task-master__set_task_status`
6. When implementation differs from plan, use `mcp__task-master__update` to update future tasks

## Development Guidelines

### Code Separation Rules
- Backend files must NOT import pygame or handle display
- Frontend files must NOT directly modify AI/NPC logic
- All communication through defined interfaces in interfaces.py

### Type Checking
The project uses Pyright for type checking. Configuration is in `pyrightconfig.json`.

### AI System Notes
- Uses OpenAI API (requires OPENAI_API_KEY environment variable)
- NPCs have persistent memory and can interact with objects
- World state is saved in JSON format in `worlds/` directory

## Important Implementation Details

### World Tick System
The AI system implements a "world tick" mechanism (from recent commits):
- Processes NPCs in parallel sequences
- Manages time and world state updates
- Found in AI_System's execute_world_tick functionality

### Data Flow
1. User input → Frontend (pygame_display) → Backend API
2. Backend processes AI logic → Returns display data
3. Frontend renders based on returned data

### Current Issues Being Addressed
- pygame_display.py is a single 1000+ line function
- backend.py contains display code in process_tick()
- Poor separation causing team collaboration issues
- Difficult to maintain and extend

## File Organization
- `worlds/`: Game world definitions and saves
- `generated_images/`: AI-generated images
- `archived_scripts/`: Old/experimental scripts
- `.taskmaster/`: Task management system files