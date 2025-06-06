# AI NPC System Refactoring Project PRD

## Overview
The AI NPC system currently suffers from significant architectural issues that impact code maintainability, team collaboration, and system scalability. The primary goal is to refactor the existing codebase to establish clear separation of concerns between frontend (pygame display) and backend (AI NPC logic), while transforming the monolithic pygame_display.py into a proper object-oriented architecture.

## Current Problems
- pygame_display.py is a giant function (~1013 lines) instead of proper OOP structure
- Backend process_tick() is contaminated with frontend display code
- Poor separation of concerns between frontend and backend
- Team collaboration issues due to mixed responsibilities
- Difficult to maintain and extend the current codebase

## Core Refactoring Objectives

### 1. Frontend Architecture Redesign
- Transform pygame_display.py from procedural to object-oriented design
- Create proper class hierarchy for display components
- Establish clear interfaces between display and game logic
- Implement proper event handling system

### 2. Backend Cleanup and Separation
- Remove all display-related code from backend.py
- Clean up process_tick() to focus only on AI logic
- Create proper APIs for frontend-backend communication
- Establish clear data contracts between layers

### 3. System Architecture Improvements
- Implement proper MVC (Model-View-Controller) pattern
- Create abstraction layers for better modularity
- Establish clear dependency injection patterns
- Improve error handling and logging systems

## Technical Architecture Refactoring

### Frontend Layer (pygame_display.py → OOP Structure)
**New Class Structure:**
- `GameDisplay` (Main display controller)
- `NPCRenderer` (Handles NPC visualization)
- `SpaceRenderer` (Handles space/world rendering)
- `ItemRenderer` (Handles item visualization)
- `UIManager` (Handles user interface components)
- `EventHandler` (Manages pygame events)
- `TerminalInterface` (Handles terminal commands)

### Backend Layer (Cleaned backend.py)
**Refactored Components:**
- `AI_System` (Pure AI logic, no display code)
- `NPC` (Clean NPC logic without display contamination)
- `WorldManager` (World state management)
- `InteractionProcessor` (Handles AI interactions)

### Communication Layer
**New Interface Classes:**
- `DisplayDataProvider` (Provides display data to frontend)
- `UserInputHandler` (Handles user input from frontend to backend)
- `StateNotifier` (Notifies frontend of backend state changes)

## Development Roadmap

### Phase 1: Backend Cleanup (Foundation)
- Extract all display-related code from backend.py
- Clean up process_tick() to be purely AI logic
- Create proper data structures for frontend-backend communication
- Implement basic API interfaces

### Phase 2: Frontend Architecture Design
- Design the new OOP class hierarchy
- Create base classes and interfaces
- Plan the data flow between components
- Design event handling system

### Phase 3: Core Display Classes Implementation
- Implement GameDisplay main controller
- Create basic renderer classes (NPC, Space, Item)
- Implement EventHandler for pygame events
- Create UIManager for interface components

### Phase 4: Advanced Features Migration
- Migrate terminal interface functionality
- Implement proper state management
- Add error handling and logging
- Optimize rendering performance

### Phase 5: Integration and Testing
- Integrate all refactored components
- Ensure feature parity with original system
- Add comprehensive testing
- Documentation and team onboarding

## Logical Dependency Chain

### Foundation First (Backend Cleanup)
1. **Backend Purification** - Remove all frontend code from backend.py
2. **API Definition** - Create clear interfaces between layers
3. **Data Contracts** - Establish what data flows between frontend/backend

### Display System Reconstruction
4. **Core Display Framework** - Basic OOP structure for pygame_display
5. **Rendering Engine** - Modular rendering components
6. **Event System** - Proper event handling architecture
7. **UI Components** - User interface management

### Integration and Enhancement
8. **System Integration** - Connect all refactored components
9. **Feature Migration** - Ensure all existing features work
10. **Performance Optimization** - Optimize the new architecture

## Team Collaboration Improvements

### Clear Responsibilities
- **Backend Team**: Focus on AI logic, world management, NPC behavior
- **Frontend Team**: Focus on display, UI, user interaction, pygame components
- **Integration Team**: Handle the communication layer between frontend/backend

### Development Guidelines
- Backend code should never import pygame or handle display
- Frontend code should never directly modify AI/NPC logic
- All communication through defined interfaces
- Proper testing for each layer

## Technical Specifications

### Backend API Requirements
```python
# Example interface for cleaned backend
class NPCManager:
    def get_npc_display_data(self) -> List[NPCDisplayData]
    def process_user_input(self, input_data: UserInput) -> None
    def get_world_state(self) -> WorldState

class InteractionAPI:
    def trigger_npc_action(self, npc_id: str) -> ActionResult
    def get_history(self, npc_id: str) -> List[HistoryEntry]
```

### Frontend Architecture Requirements
```python
# Example OOP structure for display
class GameDisplay:
    def __init__(self, backend_api: BackendAPI)
    def render_frame(self) -> None
    def handle_events(self) -> None
    def update(self) -> None

class NPCRenderer:
    def render_npcs(self, npcs: List[NPCDisplayData]) -> None
    def render_chat_bubble(self, npc_id: str, text: str) -> None
```

## Success Criteria

### Code Quality Metrics
- pygame_display.py broken into 5-8 focused classes
- Backend.py reduced by removing all display code
- Clear separation: no pygame imports in backend
- No AI/NPC logic in frontend classes

### Maintainability Improvements
- Each class has single responsibility
- Clear interfaces between components
- Easy to add new features without touching other layers
- Team members can work independently on their layers

### Performance Goals
- Maintain or improve current performance
- Better memory management through proper OOP
- Cleaner event handling reducing lag

## Risk Mitigation

### Technical Risks
- **Data Loss During Refactoring**: Implement comprehensive backup and version control
- **Feature Regression**: Maintain feature parity checklist
- **Performance Degradation**: Profile before/after refactoring

### Team Coordination Risks
- **Merge Conflicts**: Clear file ownership and modular development
- **Communication Gaps**: Regular integration testing
- **Knowledge Transfer**: Comprehensive documentation of new architecture

## Success Metrics

### Immediate Goals
- [ ] pygame_display.py converted to OOP with <200 lines per class
- [ ] Backend.py contains zero display/pygame code
- [ ] Clean interfaces between frontend and backend
- [ ] All existing features working with new architecture

### Long-term Benefits
- [ ] Faster development velocity for new features
- [ ] Easier team collaboration
- [ ] Better code maintainability
- [ ] Cleaner git history and merge conflicts reduction

## Appendix

### Current Code Issues Analysis
- pygame_display.py: 1013 lines, single giant function
- backend.py: Contains frontend code in process_tick()
- Mixed responsibilities throughout the codebase
- Difficult team collaboration due to coupled code

### New Architecture Benefits
- Modular development allowing parallel work
- Clear testing boundaries
- Better error isolation
- Easier feature addition and modification
- Professional-grade code organization 