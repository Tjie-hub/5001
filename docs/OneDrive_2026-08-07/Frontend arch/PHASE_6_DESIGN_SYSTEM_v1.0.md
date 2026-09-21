# PHASE 6 — DESIGN SYSTEM

**Document:** PHASE_6_DESIGN_SYSTEM_v1.0.md

**Version:** 1.0.0

**Status:** FROZEN

**Owner:** Product & UX Architecture

**Depends On:**

- PHASE_4_UX_BLUEPRINT_v1.0.md
- PHASE_5_WIREFRAMES_v1.0.md

**Supersedes**

None

---

# Revision History

| Version | Date | Author | Description |
|----------|------|---------|-------------|
| 1.0.0 | YYYY-MM-DD | Architecture Team | Initial frozen release |

---

# Approval

| Review Area | Status |
|-------------|--------|
| Product Architecture | Approved |
| UX Architecture | Approved |
| UI Architecture | Approved |
| Frontend Architecture | Approved |
| Engineering Governance | Approved |

Overall Status

**APPROVED**

---

# Purpose

This document defines the canonical Design System for the Decision Operating System.

The Design System transforms the structural architecture established by the UX Blueprint (Phase 4) and the Wireframe Specification (Phase 5) into a consistent, reusable, and implementation-ready visual language.

The Design System standardizes:

- Visual language
- Design principles
- Color architecture
- Typography
- Spacing
- Design Tokens
- Component Library
- Responsive behavior
- Accessibility
- Governance

This specification serves as the single source of truth for frontend visual implementation.

---

# Scope

This document governs every reusable visual element within the application.

Included:

- Design Foundations
- Visual Language
- Design Tokens
- Shared Components
- Data Visualization
- Responsive Design
- Accessibility
- Governance

Excluded:

- Backend implementation
- Business logic
- API contracts
- Frontend framework implementation
- CSS implementation

---

# Objectives

The Design System shall:

1. Create a unified visual language.
2. Standardize reusable UI components.
3. Improve analytical efficiency.
4. Reduce cognitive load.
5. Ensure accessibility.
6. Support responsive layouts.
7. Eliminate visual inconsistency.
8. Enable scalable frontend development.

---

# Design Philosophy

The Decision Operating System is an analytical platform rather than a marketing website.

Visual design shall prioritize:

- clarity
- trust
- consistency
- readability
- analytical efficiency

Decoration shall never compete with information.

---

# Design Principles

The Design System follows the principles established in Phase 6.

Core principles include:

- Information First
- Consistency Before Creativity
- Recognition Over Recall
- Progressive Disclosure
- Functional Whitespace
- Predictable Interaction
- Accessibility by Default
- Responsive by Design

Every visual decision shall align with these principles.

---

# Table of Contents

## Workstream A — Design Foundations

- P6-01 Design Principles
- P6-02 Visual Language
- P6-03 Color System
- P6-04 Typography System
- P6-05 Spacing & Grid
- P6-06 Elevation & Shadows
- P6-07 Motion Principles

---

## Workstream B — Design Tokens

- P6-08 Design Tokens
- P6-09 Color Tokens
- P6-10 Typography Tokens
- P6-11 Spacing Tokens
- P6-12 Radius & Border Tokens
- P6-13 Iconography Tokens
- P6-14 Theme Tokens

---

## Workstream C — Core Components

- P6-15 Buttons
- P6-16 Inputs
- P6-17 Dropdowns
- P6-18 Tables
- P6-19 Cards
- P6-20 Charts
- P6-21 Tabs
- P6-22 Breadcrumbs
- P6-23 Toolbars
- P6-24 Navigation Components

---

## Workstream D — Advanced Components

- P6-25 Dialogs
- P6-26 Drawers
- P6-27 Notifications
- P6-28 Toasts
- P6-29 Progress Indicators
- P6-30 Empty State Components
- P6-31 Error State Components
- P6-32 Loading Skeleton Components

---

## Workstream E — Data Visualization

- P6-33 Chart Standards
- P6-34 KPI Cards
- P6-35 Tables & Grids
- P6-36 Heatmaps
- P6-37 Dashboard Composition

---

## Workstream F — Responsive System

- P6-38 Desktop Design Rules
- P6-39 Tablet Design Rules
- P6-40 Mobile Design Rules
- P6-41 Adaptive Components

---

## Workstream G — Accessibility

- P6-42 Accessibility Standards
- P6-43 Keyboard Interaction System
- P6-44 Screen Reader Standards
- P6-45 Color Contrast & WCAG

---

## Workstream H — Governance

- P6-46 Component Naming
- P6-47 Figma Organization
- P6-48 Versioning & Change Control
- P6-49 Design System Audit
- P6-50 Final Freeze

---

# Workstream A — Design Foundations

# Workstream A — Design Foundations

---

# P6-01 — Design Principles

## Purpose

This section establishes the fundamental design principles governing the Decision Operating System.

Unlike Phase 5, which defines structural layouts, Phase 6 defines the visual language that will be consistently applied across every interface.

These principles serve as the foundation for all future visual decisions.

---

## Scope

This section defines:

- Design philosophy
- Visual priorities
- Information hierarchy
- Component philosophy
- Consistency principles
- Design constraints

This section does not define:

- Color values
- Typography scales
- Component implementations
- CSS rules
- UI framework decisions

---

## Objectives

The Design System shall:

1. Create a unified visual language.
2. Improve analytical efficiency.
3. Reduce cognitive load.
4. Ensure consistency.
5. Enable reusable components.
6. Support accessibility.
7. Scale to future modules.

---

## Core Design Philosophy

The Decision Operating System is an analytical platform.

It is not intended to function as a marketing website.

Visual design shall prioritize:

- Information
- Clarity
- Efficiency
- Trust
- Consistency

Decoration shall never compete with analytical content.

---

## Design Principles

### DS-01 — Information First

Information is always more important than decoration.

Visual styling shall improve understanding rather than attract attention.

---

### DS-02 — Consistency Before Creativity

Equivalent actions shall always appear identical.

Users should never need to relearn interactions.

---

### DS-03 — Recognition Over Recall

Users should recognize navigation, actions, and interaction patterns immediately.

The interface shall minimize reliance on memory.

---

### DS-04 — Progressive Disclosure

Present essential information first.

Reveal advanced functionality only when appropriate.

---

### DS-05 — Visual Hierarchy

Important information receives greater visual emphasis.

Hierarchy shall primarily be created through:

- Layout
- Typography
- Spacing
- Alignment

Color shall reinforce hierarchy rather than define it.

---

### DS-06 — Functional Whitespace

Whitespace separates concepts.

Whitespace is functional rather than decorative.

---

### DS-07 — Purposeful Elements

Every visible interface element must justify its existence.

Decorative components without functional value are prohibited.

---

## Analytical Design Principles

The interface shall optimize analytical workflows through:

- High information density
- Rapid scanning
- Low interaction cost
- Predictable layouts
- Reusable structures

---

## Decision Support Principles

Decision-support screens shall emphasize:

- Evidence
- Confidence
- Uncertainty
- Traceability

The interface shall never imply certainty where uncertainty exists.

---

## Navigation Principles

Visual styling shall reinforce the navigation architecture established in Phase 4.

The Design System shall never alter:

- Workspace hierarchy
- Routing
- Navigation ownership
- Context ownership

Visual changes shall not modify behavior.

---

## Component Philosophy

Reusable components shall be:

- Independent
- Predictable
- Composable
- Accessible
- Reusable

Components shall not contain hidden business logic.

---

## Data Visualization Philosophy

Charts and tables exist to communicate information.

Visualization shall prioritize:

- Accuracy
- Readability
- Comparability
- Accessibility

Visual effects shall never distort data.

---

## Interaction Philosophy

Interactions shall be:

- Immediate
- Predictable
- Consistent
- Reversible where appropriate

Every user action shall produce immediate feedback.

---

## Accessibility Philosophy

Accessibility is a primary design requirement.

The Design System targets:

WCAG 2.2 Level AA

Accessibility shall be incorporated into every component rather than added afterward.

---

## Responsive Philosophy

Desktop is the primary analytical environment.

Tablet and Mobile adapt presentation only.

Navigation architecture remains unchanged.

---

## Scalability Principles

The Design System shall support:

- Additional workspaces
- Additional components
- Additional themes
- Future analytical modules

Scalability shall not require redesigning existing components.

---

## Anti-Patterns

The following are prohibited:

- Decorative dashboards
- Excessive animation
- Inconsistent layouts
- Hidden navigation
- Multiple interaction models
- Color-only communication
- Duplicate components

---

## Validation Checklist

- Design philosophy documented
- Design principles established
- Navigation philosophy documented
- Component philosophy documented
- Accessibility philosophy documented
- Scalability principles documented

---

## Exit Criteria

P6-01 is complete when the Design System philosophy has been formally approved and frozen.

---

# P6-02 — Visual Language

## Purpose

This section defines the visual identity of the Decision Operating System.

The Visual Language transforms the Design Principles into practical visual rules that remain consistent across every workspace.

---

## Design Goals

The visual language shall communicate:

- Professionalism
- Trust
- Precision
- Stability
- Analytical clarity

The interface shall avoid unnecessary visual complexity.

---

## Visual Characteristics

The interface shall be:

- Clean
- Minimal
- Structured
- Data-centric
- Calm
- Predictable

---

## Visual Hierarchy

Hierarchy shall be established using:

1. Layout
2. Typography
3. Spacing
4. Contrast
5. Color
6. Motion

Color is not the primary mechanism for hierarchy.

---

## Information Density

The Design System targets professional analytical users.

Layouts shall maximize useful information while preserving readability.

---

## Icon Philosophy

Icons supplement text.

Icons shall never replace labels for critical actions.

---

## Illustration Policy

Illustrations are permitted only for:

- Empty States
- Onboarding
- Error Pages

Analytical workspaces shall not contain decorative illustrations.

---

## Branding

Branding shall remain subtle.

The application interface prioritizes analytical content over corporate identity.

---

## Validation Checklist

- Visual identity documented
- Visual hierarchy documented
- Information density defined
- Illustration policy documented

---

## Exit Criteria

P6-02 is complete when the Visual Language has been approved and frozen.

---

# P6-03 — Color System

## Purpose

This section defines the semantic color architecture of the Design System.

Colors communicate meaning rather than decoration.

---

## Color Categories

The Design System defines the following semantic categories:

- Primary
- Secondary
- Neutral
- Success
- Warning
- Danger
- Information

---

## Functional Categories

Colors are applied to:

- Background
- Surface
- Border
- Text
- Interactive Elements
- Feedback
- Charts

---

## Semantic Usage

Business meaning determines color usage.

Examples:

| Meaning | Category |
|----------|----------|
| Positive | Success |
| Negative | Danger |
| Neutral | Secondary |
| Information | Information |

---

## Color Hierarchy

Background

↓

Surface

↓

Content

↓

Interactive

↓

Feedback

---

## Color Independence

Information shall never rely solely on color.

Status indicators shall include one or more additional cues:

- Label
- Icon
- Pattern
- Shape

---

## Theme Compatibility

The color architecture shall support:

- Light Theme
- Dark Theme
- Future Themes

Changing themes shall require changing token values rather than component implementations.

---

## Validation Checklist

- Semantic color architecture documented
- Functional hierarchy defined
- Theme compatibility documented

---

## Exit Criteria

P6-03 is complete when the Color System has been approved and frozen.

---

# P6-04 — Typography System

## Purpose

This section defines the canonical Typography System for the Decision Operating System.

Typography establishes visual hierarchy, readability, consistency, and efficient information scanning across every workspace.

Typography shall be treated as a reusable system rather than individual font selections.

---

## Objectives

The Typography System shall:

- maximize readability
- support analytical workflows
- establish consistent hierarchy
- improve scanning efficiency
- remain accessible
- support responsive layouts

---

## Typography Philosophy

Typography communicates structure before decoration.

The Design System prioritizes:

- readability
- consistency
- hierarchy
- accessibility

Decorative typography is prohibited.

---

## Typography Hierarchy

The Design System defines the following hierarchy.

| Level | Purpose |
|---------|----------|
| Display | Landing titles |
| H1 | Workspace title |
| H2 | Major section |
| H3 | Card title |
| H4 | Subsection |
| Body | General content |
| Caption | Supporting information |
| Label | Inputs & controls |
| Code | Technical values |

---

## Reading Hierarchy

Visual emphasis follows:

Display

↓

H1

↓

H2

↓

H3

↓

H4

↓

Body

↓

Caption

↓

Label

---

## Alignment Rules

Default alignment:

Left

Numeric values:

Right

Centered text is reserved for:

- Empty states
- Status pages
- Landing illustrations

---

## Text Length

Recommended line length:

50–90 characters

Very long paragraphs shall be divided into smaller sections.

---

## Numerical Typography

Financial and analytical values shall:

- align vertically
- preserve decimal precision
- maintain consistent formatting
- use tabular figures where supported

---

## Typography Consistency

Equivalent UI elements shall use identical typography.

Example:

Every primary button uses the same typography.

Every table header uses the same typography.

Every workspace title uses the same typography.

---

## Accessibility

Typography shall support:

- browser zoom
- scalable fonts
- high contrast
- screen readers

Target:

WCAG 2.2 AA

---

## Anti-Patterns

The following are prohibited:

- Decorative fonts
- Multiple font families without purpose
- Inconsistent heading hierarchy
- Tiny unreadable text
- Center-aligned analytical tables

---

## Validation Checklist

- Typography hierarchy documented
- Alignment rules documented
- Numerical typography documented
- Accessibility documented

---

## Exit Criteria

P6-04 is complete when the Typography System is approved and frozen.

---

# P6-05 — Spacing & Grid

## Purpose

This section defines the spatial organization of the Design System.

Spacing communicates relationships between information.

Every layout shall align to a consistent grid.

---

## Objectives

The spacing system shall:

- improve readability
- reinforce hierarchy
- simplify implementation
- eliminate arbitrary spacing
- support responsive layouts

---

## Grid Philosophy

Every screen follows a common spatial framework.

Three grid levels exist:

- Page Grid
- Workspace Grid
- Component Grid

---

## Page Grid

The Page Grid defines the application shell.

It governs:

- Header
- Sidebar
- Workspace
- Footer

The Page Grid remains identical throughout the application.

---

## Workspace Grid

The Workspace Grid organizes:

- Dashboard layouts
- Cards
- Tables
- Charts
- Panels

Every workspace inherits the same alignment system.

---

## Component Grid

Component Grid controls internal spacing.

Examples:

- Card padding
- Form spacing
- Table cell spacing
- Toolbar spacing

---

## Spacing Scale

The Design System uses logical spacing tokens.

XS

↓

S

↓

M

↓

L

↓

XL

↓

2XL

Actual measurements are defined by Design Tokens.

---

## Alignment Rules

Every component aligns to the grid.

Arbitrary positioning is prohibited.

---

## Whitespace Rules

Whitespace separates:

- Sections
- Components
- Actions
- Information groups

Whitespace shall never be considered unused space.

---

## Responsive Behavior

Grid adapts across:

- Desktop
- Tablet
- Mobile

Hierarchy remains identical.

Only presentation changes.

---

## Accessibility

Consistent spacing improves:

- readability
- touch interaction
- scanning
- focus visibility

---

## Anti-Patterns

The following are prohibited:

- Arbitrary margins
- Random padding
- Misaligned components
- Uneven card spacing
- Manual pixel adjustments outside tokens

---

## Validation Checklist

- Grid hierarchy documented
- Spacing scale documented
- Alignment rules documented
- Accessibility documented

---

## Exit Criteria

P6-05 is complete when the Spacing & Grid System is approved and frozen.

---

# P6-06 — Elevation & Shadows

## Purpose

This section defines the elevation model used throughout the Design System.

Elevation communicates interface layers rather than visual decoration.

---

## Objectives

Elevation shall:

- communicate depth
- indicate interaction
- preserve hierarchy
- remain subtle
- remain consistent

---

## Elevation Philosophy

Elevation communicates:

- focus
- layering
- temporary interaction

Elevation shall never communicate importance.

---

## Elevation Levels

The Design System defines five logical levels.

| Level | Usage |
|---------|--------|
| 0 | Base surface |
| 1 | Cards |
| 2 | Dropdowns |
| 3 | Drawers |
| 4 | Dialogs / Modals |

---

## Layer Hierarchy

Surface

↓

Card

↓

Dropdown

↓

Drawer

↓

Dialog

---

## Shadow Rules

Shadows shall:

- remain subtle
- be consistent
- support layering
- never distract

---

## Accessibility

Elevation shall never be the only indicator of:

- focus
- interaction
- selection

Additional cues shall always exist.

---

## Responsive Behavior

Elevation hierarchy remains identical across:

- Desktop
- Tablet
- Mobile

---

## Anti-Patterns

The following are prohibited:

- Heavy decorative shadows
- Multiple shadow styles
- Inconsistent elevation
- Elevation indicating business priority

---

## Validation Checklist

- Elevation hierarchy documented
- Layer rules documented
- Accessibility documented

---

## Exit Criteria

P6-06 is complete when the Elevation Model is approved and frozen.

---

# P6-07 — Motion Principles

## Purpose

This section defines the motion philosophy of the Design System.

Motion communicates change.

Motion shall never become decoration.

---

## Objectives

Motion shall:

- guide attention
- explain transitions
- confirm actions
- reduce confusion
- remain subtle

---

## Motion Philosophy

Motion exists only when it improves understanding.

Animation without purpose is prohibited.

---

## Motion Categories

The Design System supports:

- Navigation
- Transition
- Feedback
- Loading
- Attention

---

## Motion Characteristics

Motion shall be:

- Smooth
- Predictable
- Brief
- Interruptible

---

## Appropriate Uses

Motion is appropriate for:

- Dialog opening
- Drawer transition
- Toast appearance
- Loading indicators
- Page transition

---

## Reduced Motion

When users request reduced motion:

- unnecessary animation is removed
- interaction remains identical
- accessibility is preserved

---

## Performance

Motion shall:

- avoid blocking interaction
- avoid layout shifts
- preserve responsiveness

---

## Anti-Patterns

The following are prohibited:

- Decorative animation
- Flashing elements
- Infinite looping without purpose
- Motion delaying interaction
- Motion replacing feedback

---

## Validation Checklist

- Motion philosophy documented
- Motion categories documented
- Reduced motion documented
- Accessibility documented

---

## Exit Criteria

P6-07 is complete when the Motion Principles are approved and frozen.

---

# Workstream B — Design Tokens

---

# P6-08 — Design Tokens

## Purpose

This section defines the canonical Design Token Architecture for the Decision Operating System.

Design Tokens are the single source of truth for all reusable visual properties used throughout the Design System.

Every visual attribute shall originate from a Design Token rather than hard-coded values.

---

## Objectives

The token architecture shall:

- centralize visual decisions
- eliminate duplicated values
- simplify maintenance
- enable theming
- improve consistency
- support future expansion

---

## Token Hierarchy

The Design System uses a three-layer hierarchy.

Core Tokens

↓

Semantic Tokens

↓

Component Tokens

Each layer builds upon the previous layer.

---

## Core Tokens

Core Tokens define primitive values.

Examples:

- Color palette
- Typography scale
- Spacing scale
- Radius
- Border width
- Elevation
- Motion duration
- Opacity

Core Tokens never reference UI components.

---

## Semantic Tokens

Semantic Tokens describe intent.

Examples:

- Primary Background
- Secondary Background
- Primary Text
- Border Default
- Success
- Warning
- Danger

Semantic Tokens hide implementation details.

---

## Component Tokens

Component Tokens apply semantic values to components.

Examples:

- Button Background
- Card Shadow
- Dialog Surface
- Input Border
- Table Header
- Navigation Background

Components consume only Component Tokens.

---

## Token Categories

The Design System defines the following categories:

- Color
- Typography
- Spacing
- Radius
- Border
- Elevation
- Motion
- Opacity
- Icon
- Z-Index

---

## Naming Convention

Structure:

Category

↓

Purpose

↓

Variant

↓

State

Example:

color.background.primary.default

button.primary.background.hover

table.header.background.default

spacing.layout.large

---

## Ownership

| Layer | Owner |
|--------|--------|
| Core Tokens | Design System |
| Semantic Tokens | Design System |
| Component Tokens | Component Library |

Application code consumes tokens but does not redefine them.

---

## Theme Compatibility

The hierarchy supports:

- Light Theme
- Dark Theme
- Future Themes

Changing themes modifies token values rather than component implementations.

---

## Governance

Changes to:

- Core Tokens
- Semantic Tokens
- Token hierarchy

require Design System approval.

---

## Validation Checklist

- Token hierarchy documented
- Categories documented
- Naming convention documented
- Ownership documented
- Governance documented

---

## Exit Criteria

P6-08 is complete when the Design Token Architecture is approved and frozen.

---

# P6-09 — Color Tokens

## Purpose

This section defines reusable Color Tokens derived from the semantic Color System.

Components shall consume Color Tokens rather than raw color values.

---

## Objectives

Color Tokens shall:

- eliminate duplicated colors
- enable theme switching
- improve consistency
- simplify maintenance

---

## Token Hierarchy

Core Colors

↓

Semantic Colors

↓

Component Colors

Components shall never reference Core Colors directly.

---

## Token Categories

Background

Surface

Text

Border

Interactive

Success

Warning

Danger

Information

Chart

---

## Naming Convention

Examples:

color.background.primary

color.surface.default

color.text.primary

color.border.default

color.status.success

color.status.warning

color.status.danger

color.interactive.primary

---

## Interactive States

Interactive colors support:

- Default
- Hover
- Focus
- Active
- Disabled

---

## Theme Support

Each Color Token provides values for:

- Light Theme
- Dark Theme

Future themes inherit the same architecture.

---

## Accessibility

Color Tokens shall support:

- WCAG 2.2 AA
- Focus visibility
- Status differentiation
- Color-independent communication

---

## Anti-Patterns

The following are prohibited:

- Hard-coded HEX values
- Component-specific colors
- Duplicate semantic colors
- Theme-specific component styling

---

## Validation Checklist

- Token hierarchy documented
- Naming standardized
- Theme support documented
- Accessibility documented

---

## Exit Criteria

P6-09 is complete when the Color Token architecture is approved and frozen.

---

# P6-10 — Typography Tokens

## Purpose

This section defines reusable Typography Tokens.

Typography Tokens provide a consistent foundation for every textual element in the application.

---

## Objectives

Typography Tokens shall:

- standardize typography
- eliminate duplicated values
- simplify responsive scaling
- improve accessibility

---

## Token Categories

The Design System defines tokens for:

- Font Family
- Font Size
- Font Weight
- Line Height
- Letter Spacing
- Paragraph Spacing

---

## Typography Scale

The logical typography hierarchy is:

Display

↓

H1

↓

H2

↓

H3

↓

H4

↓

Body

↓

Caption

↓

Label

↓

Code

---

## Naming Convention

Examples:

typography.display

typography.h1

typography.h2

typography.body

typography.caption

typography.label

typography.code

---

## Component Usage

Examples:

Button

↓

typography.label

Card Title

↓

typography.h3

Workspace Header

↓

typography.h1

Table Header

↓

typography.label

---

## Responsive Behavior

Typography Tokens preserve hierarchy across:

- Desktop
- Tablet
- Mobile

Only scale adapts.

Hierarchy remains unchanged.

---

## Accessibility

Typography Tokens shall support:

- browser zoom
- scalable fonts
- high contrast
- screen readers

---

## Governance

Typography Tokens shall never be duplicated within individual components.

Updates occur only through the Design System.

---

## Validation Checklist

- Categories documented
- Hierarchy documented
- Naming documented
- Responsive behavior documented
- Accessibility documented

---

## Exit Criteria

P6-10 is complete when Typography Tokens are approved and frozen.

---
# P6-11 — Spacing Tokens

## Purpose

This section defines reusable Spacing Tokens used throughout the Design System.

Spacing Tokens ensure consistent layouts by eliminating arbitrary margins, padding, and gaps.

Every spacing value shall originate from the token system.

---

## Objectives

Spacing Tokens shall:

- standardize spacing
- improve layout consistency
- simplify responsive adaptation
- reduce implementation complexity
- support reusable components

---

## Token Categories

The Design System defines the following spacing tokens:

spacing.xs

spacing.s

spacing.m

spacing.l

spacing.xl

spacing.2xl

Actual measurements are implementation-specific and maintained within the Design Token registry.

---

## Usage Categories

Spacing Tokens apply to:

- Margin
- Padding
- Gap
- Grid
- Section spacing
- Component spacing
- Layout spacing

---

## Layout Hierarchy

Spacing is applied consistently across the following levels.

Page

↓

Workspace

↓

Section

↓

Component

↓

Element

---

## Responsive Behavior

Spacing Tokens preserve proportional relationships across:

- Desktop
- Tablet
- Mobile

Only token values adapt.

Layout hierarchy remains unchanged.

---

## Accessibility

Consistent spacing improves:

- readability
- touch interaction
- focus visibility
- visual scanning

---

## Governance

Spacing values shall never be hard-coded inside individual components.

All spacing originates from Design Tokens.

---

## Anti-Patterns

The following are prohibited:

- Arbitrary spacing
- Random margins
- Random padding
- Negative spacing without architectural approval
- Manual pixel adjustments

---

## Validation Checklist

- Token hierarchy documented
- Usage categories documented
- Responsive behavior documented
- Accessibility documented

---

## Exit Criteria

P6-11 is complete when Spacing Tokens are approved and frozen.

---

# P6-12 — Radius & Border Tokens

## Purpose

This section defines reusable Radius and Border Tokens.

These tokens provide consistent visual boundaries throughout the application.

---

## Objectives

Radius & Border Tokens shall:

- standardize component appearance
- simplify implementation
- improve consistency
- support theme switching

---

## Radius Tokens

Logical hierarchy:

radius.none

↓

radius.small

↓

radius.medium

↓

radius.large

↓

radius.round

Actual measurements are maintained in the Design Token registry.

---

## Border Tokens

Border hierarchy:

border.default

border.subtle

border.strong

border.focus

border.error

---

## Component Mapping

Examples:

| Component | Radius |
|-----------|---------|
| Button | Medium |
| Input | Medium |
| Card | Large |
| Dialog | Large |
| Badge | Round |

---

## Border Usage

Borders communicate:

- separation
- grouping
- focus
- validation
- interaction

Borders shall never be decorative.

---

## Theme Compatibility

Radius remains identical across themes.

Border appearance may vary through Theme Tokens while preserving semantic meaning.

---

## Accessibility

Focus borders shall remain clearly distinguishable.

Border styling shall never rely solely on color.

---

## Governance

Component-specific border styles are prohibited.

All reusable borders originate from Border Tokens.

---

## Validation Checklist

- Radius hierarchy documented
- Border hierarchy documented
- Component mapping documented
- Accessibility documented

---

## Exit Criteria

P6-12 is complete when Radius & Border Tokens are approved and frozen.

---

# P6-13 — Iconography Tokens

## Purpose

This section defines reusable Iconography Tokens.

Icons communicate meaning while supporting textual labels.

Icons supplement information rather than replace it.

---

## Objectives

The icon system shall:

- improve recognition
- remain consistent
- support accessibility
- simplify navigation
- reduce visual ambiguity

---

## Icon Categories

Navigation

Actions

Status

Analytics

System

Feedback

Documents

Communication

---

## Naming Convention

Examples:

icon.search

icon.refresh

icon.export

icon.settings

icon.warning

icon.success

icon.error

icon.help

---

## Size Hierarchy

The Design System supports:

Small

↓

Medium

↓

Large

↓

Extra Large

Actual dimensions are implementation-specific.

---

## Usage Rules

Icons shall:

- accompany labels
- remain visually consistent
- support analytical workflows
- preserve semantic meaning

Critical actions shall never rely solely on icons.

---

## Accessibility

Interactive icons require:

- accessible names
- keyboard interaction
- visible focus
- screen reader support

Decorative icons shall remain hidden from assistive technologies.

---

## Theme Compatibility

Icon appearance shall adapt through Theme Tokens.

Meaning shall remain unchanged.

---

## Governance

Custom icons require Design System approval.

Existing icons shall not be duplicated.

---

## Validation Checklist

- Categories documented
- Naming documented
- Sizes documented
- Accessibility documented

---

## Exit Criteria

P6-13 is complete when Iconography Tokens are approved and frozen.

---

# P6-14 — Theme Tokens

## Purpose

This section defines the Theme Token architecture used by the Design System.

Themes modify token values while preserving component behavior.

---

## Objectives

Theme Tokens shall:

- support multiple visual themes
- preserve usability
- simplify maintenance
- eliminate duplicate component implementations

---

## Supported Themes

The Design System supports:

- Light Theme
- Dark Theme

Future themes shall inherit the same architecture.

---

## Theme Hierarchy

Core Tokens

↓

Theme Tokens

↓

Component Tokens

↓

Application

---

## Theme Categories

Each theme provides values for:

- Background
- Surface
- Text
- Border
- Interactive
- Status
- Charts
- Shadows
- Focus
- Overlays

---

## Theme Switching

Changing themes shall:

- preserve layouts
- preserve navigation
- preserve interactions
- preserve accessibility

Only token values shall change.

---

## Accessibility

Every supported theme shall satisfy:

WCAG 2.2 AA

Accessibility shall remain equivalent across themes.

---

## Future Expansion

Additional themes shall reuse:

- Component Tokens
- Semantic Tokens
- Accessibility rules

No new component implementations are required.

---

## Governance

Adding a new theme requires:

- Design review
- Accessibility validation
- Token verification
- Documentation update

---

## Validation Checklist

- Theme hierarchy documented
- Supported themes documented
- Switching behavior documented
- Accessibility documented
- Governance documented

---

## Exit Criteria

P6-14 is complete when Theme Tokens are approved and frozen.

---
# Workstream C — Core Components

---

# P6-15 — Button Components

## Purpose

This section defines the canonical Button Component used throughout the Decision Operating System.

Buttons are the primary mechanism for initiating user actions.

Every button shall follow this specification.

---

## Objectives

Button Components shall:

- communicate action priority
- remain visually consistent
- support accessibility
- provide immediate feedback
- remain reusable

---

## Button Hierarchy

The Design System defines four button levels.

| Level | Purpose |
|---------|----------|
| Primary | Main action |
| Secondary | Alternative action |
| Tertiary | Low-emphasis action |
| Text | Inline action |

Each screen should expose one clear primary action whenever appropriate.

---

## Button Variants

Supported variants:

- Filled
- Outlined
- Ghost
- Text
- Icon

Variants remain consistent throughout the application.

---

## Component States

Every button supports:

- Default
- Hover
- Focus
- Active
- Loading
- Disabled

Each state shall be visually distinguishable.

---

## Loading State

Loading buttons:

- preserve width
- prevent duplicate actions
- provide immediate feedback

---

## Icon Usage

Icons may appear:

- Left
- Right
- Icon Only

Icons supplement labels.

Primary actions shall never rely solely on icons.

---

## Accessibility

Buttons support:

- keyboard navigation
- visible focus
- accessible names
- screen readers

Target:

WCAG 2.2 AA

---

## Responsive Behavior

Desktop

Standard buttons.

Tablet

Identical hierarchy.

Mobile

Buttons may expand to full width.

---

## Anti-Patterns

The following are prohibited:

- Multiple primary buttons
- Icon-only destructive actions
- Buttons changing width while loading
- Inconsistent placement

---

## Validation Checklist

- Hierarchy documented
- Variants documented
- States documented
- Accessibility documented

---

## Exit Criteria

P6-15 is complete when Button Components are approved and frozen.

---

# P6-16 — Input Components

## Purpose

This section defines the canonical Input Component specification.

Inputs collect structured information consistently throughout the application.

---

## Objectives

Inputs shall:

- remain recognizable
- support validation
- remain accessible
- support responsive layouts

---

## Supported Inputs

The Design System supports:

- Text
- Search
- Email
- Password
- Number
- Date
- Text Area

---

## Canonical Structure

Every input contains:

- Label
- Input Control
- Supporting Text
- Validation Message (when required)

---

## Input States

Every input supports:

- Default
- Hover
- Focus
- Filled
- Disabled
- Error
- Success

---

## Validation

Validation shall provide:

- immediate feedback
- recovery guidance
- accessible messaging

Validation shall not interrupt user workflows.

---

## Labels

Labels are mandatory.

Placeholder text shall never replace labels.

---

## Accessibility

Inputs support:

- keyboard navigation
- screen readers
- autocomplete
- logical focus order

Target:

WCAG 2.2 AA

---

## Responsive Behavior

Desktop

Standard width.

Tablet

Fluid width.

Mobile

Full-width stacked inputs.

---

## Anti-Patterns

The following are prohibited:

- Placeholder-only forms
- Hidden labels
- Inconsistent validation
- Tiny touch targets

---

## Validation Checklist

- Input hierarchy documented
- Validation documented
- Accessibility documented
- Responsive behavior documented

---

## Exit Criteria

P6-16 is complete when Input Components are approved and frozen.

---

# P6-17 — Dropdown Components

## Purpose

This section defines reusable Dropdown Components.

Dropdowns enable structured selection while maintaining consistency and accessibility.

---

## Objectives

Dropdown Components shall:

- simplify selection
- support large datasets
- remain keyboard accessible
- preserve consistency

---

## Supported Types

The Design System supports:

- Single Select
- Multi Select
- Searchable Select
- Async Select
- Grouped Select

---

## Component Structure

Each Dropdown contains:

- Label
- Selected Value
- Expand Indicator
- Options List
- Optional Search Field

---

## Component States

Supported states:

- Closed
- Open
- Hover
- Focus
- Disabled
- Error

---

## Interaction

Dropdowns support:

- keyboard navigation
- filtering
- search
- clear selection
- escape to close

---

## Accessibility

Dropdowns support:

- Arrow Keys
- Enter
- Escape
- Screen Readers
- Visible Focus

Target:

WCAG 2.2 AA

---

## Responsive Behavior

Desktop

Popover list.

Tablet

Adaptive popover.

Mobile

Bottom sheet selector.

---

## Anti-Patterns

The following are prohibited:

- Hidden selections
- Non-searchable large lists
- Inconsistent keyboard behavior
- Scroll locking failures

---

## Validation Checklist

- Types documented
- Interaction documented
- Accessibility documented
- Responsive behavior documented

---

## Exit Criteria

P6-17 is complete when Dropdown Components are approved and frozen.

---

# P6-18 — Table Components

## Purpose

This section defines the canonical Table Component used throughout the Decision Operating System.

Tables are the primary presentation mechanism for structured analytical information.

Every analytical workspace shall use the standardized Table Component.

---

## Objectives

Tables shall:

- present structured information clearly
- support rapid comparison
- remain scalable
- support accessibility
- preserve analytical efficiency

---

## Supported Table Types

The Design System supports:

- Standard Data Table
- Analytical Table
- Ranking Table
- Portfolio Table
- Watchlist Table
- Comparison Table

Each table type shares the same underlying interaction model.

---

## Canonical Structure

Every table contains:

- Toolbar
- Header Row
- Data Rows
- Pagination
- Optional Summary Row

The structure remains consistent across all workspaces.

---

## Table Features

Tables support:

- Sorting
- Filtering
- Pagination
- Column Resize
- Column Visibility
- Export
- Row Selection

Features shall remain consistent throughout the application.

---

## Column Types

Supported column types:

- Text
- Number
- Currency
- Percentage
- Date
- Badge
- Status
- Action

Each column type follows a standardized presentation.

---

## Sorting

Sorting shall:

- remain deterministic
- indicate active direction
- preserve accessibility
- announce state changes

---

## Filtering

Filtering supports:

- Quick Filters
- Advanced Filters
- Search
- Saved Filters

Filtering shall never alter original data.

---

## Selection

Tables may support:

- Single Selection
- Multi Selection
- Bulk Actions

Selection state shall remain visually distinguishable.

---

## Accessibility

Tables support:

- semantic markup
- keyboard navigation
- screen readers
- sortable announcements
- accessible pagination

Target:

WCAG 2.2 AA

---

## Responsive Behavior

Desktop

Full analytical table.

Tablet

Scrollable table.

Mobile

Responsive card transformation or simplified table.

---

## Anti-Patterns

The following are prohibited:

- Hidden columns without indication
- Infinite horizontal scrolling
- Color-only status indicators
- Inconsistent sorting behavior

---

## Validation Checklist

- Table structure documented
- Features documented
- Accessibility documented
- Responsive behavior documented

---

## Exit Criteria

P6-18 is complete when Table Components are approved and frozen.

---

# P6-19 — Card Components

## Purpose

This section defines reusable Card Components.

Cards group related analytical information into reusable visual units.

---

## Objectives

Cards shall:

- organize information
- improve scanning
- remain reusable
- preserve consistency

---

## Supported Card Types

The Design System supports:

- KPI Card
- Market Card
- Decision Card
- Portfolio Card
- Watchlist Card
- Summary Card

---

## Canonical Structure

Every card contains:

- Header
- Primary Content
- Supporting Content
- Optional Actions
- Footer (optional)

---

## Card Rules

Cards shall:

- represent one primary concept
- avoid excessive nesting
- remain independently reusable

---

## Card Variants

Supported variants:

- Static
- Interactive
- Expandable
- Selectable

Variants preserve the same structural hierarchy.

---

## Interaction

Cards may support:

- Click
- Selection
- Expansion
- Context Menu

Interaction remains optional.

---

## Accessibility

Cards support:

- semantic headings
- logical reading order
- keyboard activation (when interactive)
- screen reader compatibility

---

## Responsive Behavior

Desktop

Grid layout.

Tablet

Adaptive grid.

Mobile

Single-column stack.

---

## Anti-Patterns

The following are prohibited:

- Cards containing unrelated information
- Deep card nesting
- Inconsistent card spacing
- Cards without hierarchy

---

## Validation Checklist

- Card hierarchy documented
- Variants documented
- Interaction documented
- Accessibility documented

---

## Exit Criteria

P6-19 is complete when Card Components are approved and frozen.

---

# P6-20 — Chart Components

## Purpose

This section defines reusable Chart Components built upon the Chart Standards established in P6-33.

This specification governs reusable chart containers rather than individual visualization techniques.

---

## Objectives

Chart Components shall:

- remain reusable
- preserve consistency
- support analytical workflows
- remain accessible

---

## Supported Components

The Design System supports:

- Line Chart
- Area Chart
- Bar Chart
- Candlestick Chart
- Heatmap
- Donut Chart
- Timeline Chart
- Scatter Plot

---

## Canonical Structure

Every chart contains:

- Chart Header
- Context Information
- Controls
- Visualization Area
- Legend
- Optional Footer

---

## Chart Controls

Charts may expose:

- Timeframe
- Compare
- Filter
- Export
- Refresh

Controls remain standardized.

---

## Component States

Supported states:

- Loading
- Empty
- Error
- Interactive
- Disabled

State behavior remains identical across chart types.

---

## Interaction

Charts support:

- Hover inspection
- Keyboard navigation
- Zoom
- Pan
- Compare
- Export

Interactions shall not modify underlying business data.

---

## Accessibility

Charts provide:

- accessible titles
- textual summaries
- keyboard interaction
- screen reader compatibility

Target:

WCAG 2.2 AA

---

## Responsive Behavior

Desktop

Full visualization.

Tablet

Adaptive scaling.

Mobile

Simplified visualization while preserving meaning.

---

## Anti-Patterns

The following are prohibited:

- Decorative charts
- 3D visualizations
- Missing legends
- Missing titles
- Color-only interpretation

---

## Validation Checklist

- Chart structure documented
- Controls documented
- States documented
- Accessibility documented
- Responsive behavior documented

---

## Exit Criteria

P6-20 is complete when Chart Components are approved and frozen.

---

# P6-21 — Tab Components

## Purpose

This section defines the canonical Tab Component used throughout the Decision Operating System.

Tabs organize related content within a single workspace while preserving navigation hierarchy and user context.

Tabs shall never replace primary application navigation.

---

## Objectives

Tab Components shall:

- organize related information
- reduce visual clutter
- preserve workspace context
- support accessibility
- remain predictable

---

## Supported Usage

Tabs may be used within:

- Ticker Workspace
- Portfolio Workspace
- Decision Workspace
- Settings
- Dialogs

Tabs shall not represent application routing.

---

## Canonical Structure

Every Tab Component contains:

- Tab List
- Active Indicator
- Active Panel
- Optional Overflow

The structure remains identical across workspaces.

---

## Tab States

Supported states:

- Default
- Hover
- Focus
- Active
- Disabled

Each state shall remain visually distinguishable.

---

## Interaction

Selecting a tab shall:

- update visible content
- preserve application state
- maintain workspace ownership
- restore focus appropriately

---

## Keyboard Navigation

Tabs support:

- Left Arrow
- Right Arrow
- Home
- End
- Enter
- Space

Keyboard behavior shall remain consistent.

---

## Accessibility

Tabs provide:

- semantic tab roles
- accessible labels
- visible focus
- screen reader announcements

Target:

WCAG 2.2 AA

---

## Responsive Behavior

Desktop

Horizontal tabs.

Tablet

Scrollable horizontal tabs.

Mobile

Scrollable tabs or segmented controls.

---

## Anti-Patterns

The following are prohibited:

- Tabs replacing navigation
- Nested tab structures
- Hidden active tabs
- Inconsistent ordering

---

## Validation Checklist

- Structure documented
- States documented
- Keyboard navigation documented
- Accessibility documented

---

## Exit Criteria

P6-21 is complete when Tab Components are approved and frozen.

---

# P6-22 — Breadcrumb Components

## Purpose

This section defines the canonical Breadcrumb Component.

Breadcrumbs communicate the user's current location within the application hierarchy.

---

## Objectives

Breadcrumbs shall:

- communicate hierarchy
- support navigation
- preserve context
- remain lightweight

---

## Canonical Structure

Every breadcrumb contains:

- Root
- Parent Levels
- Current Location

Example

Home

>

Market

>

Sector

>

Ticker

---

## Navigation Rules

Breadcrumbs:

- follow routing hierarchy
- exclude dialogs
- exclude temporary overlays
- exclude filter state

---

## Interaction

Ancestor items remain selectable.

Current location is informational only.

---

## Accessibility

Breadcrumbs support:

- semantic navigation
- screen readers
- keyboard navigation

---

## Responsive Behavior

Desktop

Full hierarchy.

Tablet

Collapsed hierarchy.

Mobile

Condensed hierarchy.

---

## Anti-Patterns

The following are prohibited:

- Breadcrumb loops
- Temporary state in breadcrumbs
- Missing current page
- Inconsistent hierarchy

---

## Validation Checklist

- Structure documented
- Navigation documented
- Accessibility documented

---

## Exit Criteria

P6-22 is complete when Breadcrumb Components are approved and frozen.

---

# P6-23 — Toolbar Components

## Purpose

This section defines reusable Toolbar Components.

Toolbars expose contextual workspace actions while preserving consistency across analytical workflows.

---

## Objectives

Toolbars shall:

- expose contextual actions
- reduce interaction cost
- preserve consistency
- remain responsive

---

## Canonical Structure

Every toolbar contains:

- Primary Actions
- Secondary Actions
- Overflow Menu

---

## Supported Actions

Toolbars may include:

- Search
- Filter
- Sort
- Compare
- Refresh
- Export
- Share
- Settings

---

## Action Priority

Priority order:

Primary

↓

Secondary

↓

Overflow

Actions shall remain stable across similar workspaces.

---

## Interaction

Toolbars support:

- keyboard navigation
- shortcuts
- responsive collapsing
- overflow menus

---

## Accessibility

Toolbars provide:

- logical focus order
- screen reader support
- visible focus
- accessible controls

---

## Responsive Behavior

Desktop

Complete toolbar.

Tablet

Grouped actions.

Mobile

Overflow-first toolbar.

---

## Anti-Patterns

The following are prohibited:

- Multiple overflowing rows
- Hidden primary actions
- Random action ordering
- Duplicate controls

---

## Validation Checklist

- Structure documented
- Priority documented
- Accessibility documented
- Responsive behavior documented

---

## Exit Criteria

P6-23 is complete when Toolbar Components are approved and frozen.

---

# P6-24 — Navigation Components

## Purpose

This section defines the reusable Navigation Component Library.

Navigation Components implement the architecture established in Phase 4 while remaining visually consistent across every workspace.

---

## Objectives

Navigation Components shall:

- preserve routing
- support accessibility
- remain reusable
- remain responsive
- maintain consistency

---

## Component Library

The Navigation Library includes:

- Global Header
- Sidebar
- Navigation Drawer
- Bottom Navigation
- Breadcrumb
- Tabs
- Pagination
- Stepper

---

## Navigation Hierarchy

Application

↓

Global Header

↓

Sidebar

↓

Workspace

↓

Local Navigation

---

## Component Responsibilities

| Component | Responsibility |
|-----------|----------------|
| Global Header | Application-level actions |
| Sidebar | Workspace navigation |
| Navigation Drawer | Responsive navigation |
| Bottom Navigation | Mobile workspace switching |
| Breadcrumb | Hierarchy awareness |
| Tabs | Local content switching |
| Pagination | Dataset navigation |
| Stepper | Sequential workflows |

Each component owns exactly one navigation responsibility.

---

## Interaction Standards

Navigation Components support:

- keyboard navigation
- browser history
- focus restoration
- screen readers
- responsive adaptation

Navigation behavior remains consistent across devices.

---

## Responsive Behavior

Desktop

Persistent Sidebar.

Tablet

Collapsible Sidebar.

Mobile

Navigation Drawer + Bottom Navigation.

Hierarchy remains unchanged.

---

## Accessibility

Navigation Components satisfy:

- Landmark roles
- Keyboard navigation
- Visible focus
- Screen reader compatibility

Target:

WCAG 2.2 AA

---

## Governance

Navigation architecture shall not change outside the Architecture Decision Record (ADR) process.

Visual refinements may occur through the Design System.

---

## Anti-Patterns

The following are prohibited:

- Duplicate navigation systems
- Hidden primary navigation
- Device-specific navigation hierarchies
- Navigation bypassing routing
- Workspace-specific navigation behavior

---

## Validation Checklist

- Navigation library documented
- Responsibilities documented
- Interaction standards documented
- Accessibility documented
- Responsive behavior documented

---

## Exit Criteria

P6-24 is complete when the Navigation Component Library is approved and frozen.

---

# Workstream D — Advanced Components

---

# P6-25 — Dialog Components

## Purpose

This section defines the canonical Dialog Component for the Decision Operating System.

Dialogs temporarily interrupt user workflows to request confirmation, collect information, or communicate important status while preserving application context.

Dialogs shall never replace application navigation.

---

## Objectives

Dialog Components shall:

- preserve context
- support focused interaction
- minimize disruption
- remain accessible
- remain reusable

---

## Supported Dialog Types

The Design System supports:

- Information Dialog
- Confirmation Dialog
- Form Dialog
- Progress Dialog

Each dialog serves one primary purpose.

---

## Canonical Structure

Every dialog contains:

- Title Bar
- Content Area
- Supporting Information
- Action Bar

---

## Dialog Sizes

Supported sizes:

- Small
- Medium
- Large
- Extra Large

Dialogs shall never exceed the usable viewport.

---

## Interaction

Opening a dialog shall:

- preserve page state
- trap keyboard focus
- dim background
- disable background interaction

Closing a dialog shall:

- restore focus
- restore scroll position
- preserve application state

---

## Closing Methods

Dialogs may close through:

- Primary Action
- Secondary Action
- Close Button
- Escape Key
- Outside Click (non-critical dialogs only)

Critical confirmation dialogs shall not close accidentally.

---

## Accessibility

Dialogs support:

- keyboard navigation
- focus trapping
- semantic dialog roles
- screen readers
- visible focus

Target:

WCAG 2.2 AA

---

## Responsive Behavior

Desktop

Centered modal.

Tablet

Responsive modal.

Mobile

Bottom sheet or full-screen dialog.

---

## Anti-Patterns

The following are prohibited:

- Nested dialogs
- Background interaction
- Multiple active dialogs
- Dialogs replacing navigation

---

## Validation Checklist

- Structure documented
- Interaction documented
- Accessibility documented
- Responsive behavior documented

---

## Exit Criteria

P6-25 is complete when Dialog Components are approved and frozen.

---

# P6-26 — Drawer Components

## Purpose

This section defines reusable Drawer Components.

Drawers present contextual content without leaving the current workspace.

---

## Objectives

Drawers shall:

- preserve context
- support responsive layouts
- reduce navigation cost
- remain reusable

---

## Supported Drawers

The Design System supports:

- Navigation Drawer
- Filter Drawer
- Detail Drawer
- Settings Drawer
- Action Drawer

---

## Canonical Structure

Every drawer contains:

- Header
- Content Area
- Action Area
- Close Control

---

## Interaction

Opening a drawer:

- slides from the viewport edge
- preserves background state
- traps focus

Closing restores the previous interaction context.

---

## Responsive Behavior

Desktop

Side drawer.

Tablet

Wide drawer.

Mobile

Full-screen sheet.

---

## Accessibility

Drawers support:

- keyboard navigation
- focus trapping
- screen readers
- focus restoration

---

## Anti-Patterns

The following are prohibited:

- Nested drawers
- Hidden actions
- Drawers replacing routing
- Multiple simultaneous drawers

---

## Validation Checklist

- Structure documented
- Interaction documented
- Accessibility documented

---

## Exit Criteria

P6-26 is complete when Drawer Components are approved and frozen.

---

# P6-27 — Notification Components

## Purpose

This section defines reusable Notification Components.

Notifications communicate important application events without interrupting user workflows.

---

## Objectives

Notifications shall:

- communicate system status
- remain non-intrusive
- support accessibility
- preserve user context

---

## Notification Types

Supported notification types:

- Success
- Information
- Warning
- Error

---

## Canonical Structure

Every notification contains:

- Status Indicator
- Title
- Supporting Message
- Optional Action
- Dismiss Control

---

## Behavior

Notifications:

- appear automatically
- do not steal focus
- may auto-dismiss
- may be manually dismissed

---

## Usage

Appropriate uses include:

- Save completed
- Import completed
- Synchronization completed
- Background process completed

Notifications shall not replace confirmation dialogs.

---

## Accessibility

Notifications support:

- screen reader announcements
- semantic status roles
- keyboard dismissal

---

## Responsive Behavior

Notification behavior remains identical across:

- Desktop
- Tablet
- Mobile

Presentation adapts while behavior remains unchanged.

---

## Anti-Patterns

The following are prohibited:

- Modal notifications
- Blocking notifications
- Duplicate notifications
- Permanent notifications without justification

---

## Validation Checklist

- Notification types documented
- Behavior documented
- Accessibility documented
- Responsive behavior documented

---

## Exit Criteria

P6-27 is complete when Notification Components are approved and frozen.

---

# P6-28 — Toast Components

## Purpose

This section defines the canonical Toast Component used throughout the Decision Operating System.

Toasts provide lightweight, temporary feedback that confirms completed actions or communicates non-critical information without interrupting the user's workflow.

---

## Objectives

Toast Components shall:

- provide immediate feedback
- remain unobtrusive
- avoid workflow interruption
- support accessibility
- maintain consistency

---

## Supported Toast Types

The Design System supports:

- Success Toast
- Information Toast
- Warning Toast
- Error Toast

Toast appearance shall follow semantic status definitions established by the Design Tokens.

---

## Canonical Structure

Every Toast contains:

- Status Icon
- Title
- Optional Supporting Message
- Optional Action
- Dismiss Control

---

## Behavior

Toasts:

- appear automatically
- never receive keyboard focus automatically
- disappear automatically unless persistent
- may be dismissed manually

---

## Appropriate Usage

Use Toasts for:

- Save completed
- Export completed
- Copy completed
- Preferences updated
- Background synchronization finished

Do not use Toasts for:

- Critical errors
- Destructive confirmations
- Authentication failures
- Multi-step workflows

---

## Placement

Recommended placement:

- Top Right (Desktop)
- Top Center (Tablet)
- Bottom or Top (Mobile)

Placement remains consistent throughout the application.

---

## Accessibility

Toasts shall:

- announce status appropriately
- support keyboard dismissal
- avoid stealing focus
- expose accessible labels

Target:

WCAG 2.2 AA

---

## Responsive Behavior

Desktop

Floating notification stack.

Tablet

Compact floating stack.

Mobile

Single-column stacked presentation.

---

## Anti-Patterns

The following are prohibited:

- Modal Toasts
- Permanent Toasts without dismissal
- Multiple duplicate Toasts
- Toasts requiring user interaction before continuing work

---

## Validation Checklist

- Toast types documented
- Behavior documented
- Accessibility documented
- Responsive behavior documented

---

## Exit Criteria

P6-28 is complete when Toast Components are approved and frozen.

---

# P6-29 — Progress Indicators

## Purpose

This section defines the canonical Progress Indicator components.

Progress Indicators communicate the status of ongoing operations and improve user confidence during long-running tasks.

---

## Objectives

Progress Indicators shall:

- communicate progress clearly
- reduce uncertainty
- remain visually consistent
- support accessibility

---

## Supported Indicator Types

The Design System supports:

- Linear Progress Bar
- Circular Progress Indicator
- Indeterminate Loader
- Inline Progress Indicator

---

## Canonical Structure

Every Progress Indicator contains:

- Status Label
- Progress Visualization
- Optional Percentage
- Optional Supporting Text

---

## Indicator States

Supported states:

- Idle
- Active
- Complete
- Failed
- Cancelled

---

## Behavior

Progress Indicators shall:

- update smoothly
- avoid unnecessary animation
- communicate completion immediately
- indicate cancellation where applicable

---

## Determinate Progress

Determinate indicators display measurable progress.

Examples:

- File upload
- Portfolio import
- Data synchronization

---

## Indeterminate Progress

Indeterminate indicators communicate activity when duration cannot be estimated.

Examples:

- Authentication
- Initial loading
- Background processing

---

## Accessibility

Progress Indicators shall expose:

- current status
- completion percentage (when available)
- completion announcement
- semantic progress roles

Target:

WCAG 2.2 AA

---

## Responsive Behavior

Progress Indicators maintain identical behavior across all supported devices.

---

## Anti-Patterns

The following are prohibited:

- Endless progress animations
- Fake progress
- Missing completion feedback
- Blocking unrelated interactions unnecessarily

---

## Validation Checklist

- Indicator types documented
- States documented
- Accessibility documented

---

## Exit Criteria

P6-29 is complete when Progress Indicators are approved and frozen.

---

# P6-30 — Empty State Components

## Purpose

This section defines reusable Empty State Components.

Empty States communicate the absence of data while guiding users toward the next appropriate action.

---

## Objectives

Empty States shall:

- explain why content is absent
- suggest recovery actions
- maintain application consistency
- reduce user confusion

---

## Supported Empty States

The Design System supports:

- Empty Search
- Empty Watchlist
- Empty Portfolio
- Empty Dashboard
- Empty History
- Empty Filter Results

---

## Canonical Structure

Every Empty State contains:

- Title
- Explanation
- Primary Action
- Optional Secondary Action
- Optional Illustration

---

## Messaging Principles

Messages shall:

- remain concise
- explain the situation
- avoid technical jargon
- recommend the next action

---

## Actions

Examples include:

- Create
- Import
- Refresh
- Clear Filters
- Search Again

Every Empty State shall provide at least one recovery path.

---

## Accessibility

Empty States shall support:

- semantic headings
- logical reading order
- accessible actions
- screen reader compatibility

---

## Responsive Behavior

Presentation adapts to available space while preserving message hierarchy.

---

## Anti-Patterns

The following are prohibited:

- Blank screens
- Missing recovery actions
- Technical error messages
- Decorative-only illustrations

---

## Validation Checklist

- Empty State types documented
- Messaging documented
- Recovery actions documented
- Accessibility documented

---

## Exit Criteria

P6-30 is complete when Empty State Components are approved and frozen.

---

# P6-31 — Error State Components

## Purpose

This section defines reusable Error State Components.

Error States communicate failures while providing clear recovery guidance.

---

## Objectives

Error States shall:

- explain the problem
- preserve user trust
- recommend recovery
- remain accessible

---

## Error Categories

Supported categories:

- Network
- Validation
- Authentication
- Authorization
- Resource Not Found
- Server Error
- Unknown Error

---

## Canonical Structure

Every Error State contains:

- Error Title
- Explanation
- Recovery Action
- Optional Supporting Information

---

## Recovery Actions

Examples include:

- Retry
- Refresh
- Sign In
- Return
- Contact Support

At least one recovery path shall always be available.

---

## Error Messaging

Messages shall:

- avoid implementation details
- explain consequences
- recommend corrective action

---

## Accessibility

Error States shall:

- announce themselves appropriately
- receive focus when required
- expose accessible recovery actions

---

## Responsive Behavior

Error hierarchy remains identical across all devices.

---

## Anti-Patterns

The following are prohibited:

- Unexplained failures
- Dead-end errors
- Stack traces
- Technical implementation messages

---

## Validation Checklist

- Error categories documented
- Recovery actions documented
- Accessibility documented

---

## Exit Criteria

P6-31 is complete when Error State Components are approved and frozen.

---

# P6-32 — Loading Skeleton Components

## Purpose

This section defines reusable Loading Skeleton Components.

Skeletons preserve layout stability while data loads.

---

## Objectives

Loading Skeletons shall:

- reduce perceived latency
- prevent layout shifts
- preserve visual hierarchy
- remain consistent

---

## Supported Skeleton Types

The Design System supports:

- Card Skeleton
- Table Skeleton
- Chart Skeleton
- Form Skeleton
- Dashboard Skeleton

---

## Canonical Structure

Skeletons shall preserve the dimensions of their corresponding components.

The transition from Skeleton to Content shall not alter layout geometry.

---

## Behavior

Skeletons shall:

- appear immediately
- disappear automatically when content loads
- preserve component dimensions
- avoid excessive animation

---

## Accessibility

Skeletons shall:

- communicate loading state
- avoid unnecessary announcements
- preserve keyboard interaction where appropriate

---

## Responsive Behavior

Skeleton layouts adapt proportionally across:

- Desktop
- Tablet
- Mobile

Behavior remains identical.

---

## Anti-Patterns

The following are prohibited:

- Layout shifts after loading
- Infinite loading without timeout
- Decorative placeholder animations
- Missing loading feedback

---

## Validation Checklist

- Skeleton types documented
- Behavior documented
- Accessibility documented
- Responsive behavior documented

---

## Exit Criteria

P6-32 is complete when Loading Skeleton Components are approved and frozen.

---

# Workstream E — Data Visualization

---

# P6-33 — Chart Standards

## Purpose

This section defines the canonical Chart Standards for the Decision Operating System.

Chart Standards ensure that every visualization communicates analytical information consistently, accurately, and accessibly.

This specification governs visualization behavior rather than individual chart implementations.

---

## Objectives

Chart Standards shall:

- communicate information accurately
- maximize readability
- support comparison
- remain accessible
- remain visually consistent

---

## Visualization Principles

Every chart shall:

- answer one analytical question
- present data honestly
- avoid unnecessary decoration
- prioritize interpretation over appearance

Charts exist to support decisions.

---

## Supported Chart Types

The Design System supports:

- Line Chart
- Area Chart
- Bar Chart
- Candlestick Chart
- Scatter Plot
- Heatmap
- Donut Chart
- Timeline

Additional chart types require Design System approval.

---

## Common Structure

Every chart contains:

- Title
- Optional Subtitle
- Visualization Area
- Legend
- Axis Labels (when applicable)
- Data Source (optional)
- Last Updated Timestamp (optional)

---

## Color Usage

Charts shall use semantic Color Tokens.

Colors shall:

- remain consistent
- support accessibility
- avoid ambiguity

Color alone shall never communicate meaning.

---

## Legends

Legends shall:

- explain every series
- remain visible
- preserve ordering
- support accessibility

Interactive legends shall maintain keyboard support.

---

## Axes

Axes shall:

- contain descriptive labels
- preserve proportional scaling
- avoid misleading truncation
- display consistent formatting

---

## Tooltips

Tooltips may display:

- exact values
- timestamps
- comparisons
- metadata

Tooltips supplement rather than replace visible information.

---

## Interaction

Charts may support:

- hover inspection
- keyboard navigation
- zoom
- pan
- comparison
- export

Interaction shall never alter underlying analytical data.

---

## Accessibility

Charts shall provide:

- descriptive titles
- textual summaries
- keyboard interaction
- screen reader compatibility

Target:

WCAG 2.2 AA

---

## Responsive Behavior

Desktop

Full visualization.

Tablet

Adaptive scaling.

Mobile

Simplified presentation while preserving analytical meaning.

---

## Anti-Patterns

The following are prohibited:

- Decorative 3D charts
- Missing legends
- Missing titles
- Distorted scales
- Color-only communication
- Excessive animation

---

## Validation Checklist

- Visualization principles documented
- Supported chart types documented
- Accessibility documented
- Responsive behavior documented

---

## Exit Criteria

P6-33 is complete when the Chart Standards are approved and frozen.

---

# P6-34 — KPI Card Components

## Purpose

This section defines the canonical KPI Card Component.

KPI Cards summarize the most important analytical metrics while preserving consistency across all workspaces.

KPI Cards provide summary information rather than detailed analysis.

---

## Objectives

KPI Cards shall:

- communicate one primary metric
- support rapid scanning
- remain visually lightweight
- support comparison
- remain reusable

---

## Supported KPI Types

The Design System supports:

- Numeric KPI
- Currency KPI
- Percentage KPI
- Ratio KPI
- Count KPI
- Status KPI

---

## Canonical Structure

Every KPI Card contains:

- Title
- Primary Metric
- Supporting Metric
- Trend Indicator
- Status Indicator

Optional:

- Timestamp
- Comparison Value
- Delta

---

## Information Hierarchy

The hierarchy shall follow:

Title

↓

Primary Metric

↓

Supporting Metric

↓

Trend

↓

Status

---

## Trend Indicators

Trend indicators may communicate:

- Increase
- Decrease
- Stable

Trend visualization shall never rely solely on color.

---

## Status Indicators

Supported statuses:

- Positive
- Neutral
- Warning
- Critical

Status shall use semantic Color Tokens together with labels or icons.

---

## Interaction

KPI Cards may support:

- drill-down
- tooltip
- context menu

Interaction remains optional.

---

## Accessibility

KPI Cards support:

- semantic headings
- accessible metric descriptions
- keyboard activation (when interactive)
- screen reader compatibility

---

## Responsive Behavior

Desktop

4–6 cards per row.

Tablet

2–3 cards per row.

Mobile

Single-column stack.

Hierarchy remains unchanged.

---

## Anti-Patterns

The following are prohibited:

- Multiple primary metrics
- Decorative KPI Cards
- Hidden trend indicators
- Color-only status communication

---

## Validation Checklist

- KPI hierarchy documented
- Trend indicators documented
- Accessibility documented
- Responsive behavior documented

---

## Exit Criteria

P6-34 is complete when KPI Card Components are approved and frozen.

---

# P6-35 — Tables & Grids
# P6-35 — Tables & Grids

## Purpose

This section defines the canonical analytical Table and Grid standards for the Decision Operating System.

Tables and Grids are the primary mechanisms for presenting structured analytical information.

They shall support efficient comparison, filtering, sorting, and decision-making.

---

## Objectives

Tables & Grids shall:

- maximize readability
- support analytical workflows
- scale to large datasets
- remain accessible
- remain responsive

---

## Supported Grid Types

The Design System supports:

- Standard Data Table
- Analytical Grid
- Ranking Grid
- Comparison Grid
- Portfolio Grid
- Watchlist Grid

Each grid follows the same interaction model.

---

## Canonical Structure

Every Table contains:

- Toolbar
- Header Row
- Data Grid
- Optional Summary Row
- Pagination
- Footer

The structure remains consistent across all analytical workspaces.

---

## Column Types

Supported column types include:

- Text
- Number
- Currency
- Percentage
- Date
- Status
- Badge
- Action
- Progress

Each type follows standardized formatting rules.

---

## Sorting

Sorting shall:

- remain deterministic
- indicate sort direction
- support keyboard interaction
- preserve accessibility

Multi-column sorting may be supported where appropriate.

---

## Filtering

Filtering supports:

- Quick Filters
- Advanced Filters
- Search
- Saved Filters

Filtering shall never modify the underlying dataset.

---

## Selection

Supported selection modes:

- Single Row
- Multi Row
- Range Selection
- Bulk Selection

Selection shall remain visually distinguishable.

---

## Density Modes

Supported density modes:

- Compact
- Comfortable
- Spacious

User preference may persist between sessions.

---

## Export

Supported export targets:

- CSV
- Excel
- PDF
- Clipboard

Export shall preserve visible sorting and filtering unless explicitly configured otherwise.

---

## Accessibility

Tables shall support:

- semantic table markup
- keyboard navigation
- accessible sorting
- screen reader compatibility
- visible focus

Target:

WCAG 2.2 AA

---

## Responsive Behavior

Desktop

Full analytical table.

Tablet

Scrollable grid.

Mobile

Responsive card layout or simplified grid.

Behavior remains identical.

---

## Anti-Patterns

The following are prohibited:

- Hidden sorting
- Hidden filters
- Infinite horizontal scrolling without indication
- Color-only status indicators
- Inconsistent column alignment

---

## Validation Checklist

- Grid types documented
- Sorting documented
- Filtering documented
- Accessibility documented
- Responsive behavior documented

---

## Exit Criteria

P6-35 is complete when Tables & Grids are approved and frozen.

---

# P6-36 — Heatmap Components

## Purpose

This section defines the canonical Heatmap Component.

Heatmaps visualize relative performance across multiple entities while preserving analytical accuracy.

Heatmaps complement numerical analysis and never replace underlying data.

---

## Objectives

Heatmaps shall:

- communicate comparative performance
- maximize visual scanning
- support interaction
- remain accessible

---

## Supported Use Cases

Heatmaps may be used for:

- Market Overview
- Sector Performance
- Portfolio Allocation
- Watchlist Performance
- Decision Distribution
- Risk Distribution

---

## Canonical Structure

Every Heatmap contains:

- Title
- Optional Subtitle
- Heatmap Grid
- Legend
- Optional Filters

---

## Cell Behavior

Each cell shall expose:

- Label
- Value
- Category
- Tooltip

Cells remain individually accessible.

---

## Color Usage

Heatmaps use semantic Color Tokens.

Color shall communicate relative magnitude.

Color alone shall never communicate meaning.

---

## Legend

Legends shall:

- explain every color range
- remain visible
- preserve ordering
- support accessibility

---

## Interaction

Supported interactions:

- Hover
- Selection
- Tooltip
- Drill-down
- Compare

Interaction shall never alter source data.

---

## Accessibility

Heatmaps shall provide:

- textual summaries
- keyboard navigation
- accessible labels
- screen reader compatibility

Target:

WCAG 2.2 AA

---

## Responsive Behavior

Desktop

Full heatmap.

Tablet

Adaptive grid.

Mobile

Scrollable or summarized presentation.

---

## Anti-Patterns

The following are prohibited:

- Missing legends
- Decorative gradients
- Color-only interpretation
- Distorted cell sizing
- Hidden values

---

## Validation Checklist

- Supported use cases documented
- Interaction documented
- Accessibility documented
- Responsive behavior documented

---

## Exit Criteria

P6-36 is complete when Heatmap Components are approved and frozen.

---

# P6-37 — Dashboard Composition

## Purpose

This section defines the canonical Dashboard Composition architecture.

Dashboards organize analytical information into predictable layouts supporting rapid decision-making.

Every dashboard shall follow the same visual hierarchy.

---

## Objectives

Dashboard Composition shall:

- prioritize critical information
- improve analytical efficiency
- preserve consistency
- support scalability
- remain responsive

---

## Dashboard Philosophy

Dashboards answer analytical questions in the following sequence:

1. Current Status
2. Key Metrics
3. Trends
4. Supporting Evidence
5. Detailed Data

---

## Canonical Layout

Every dashboard consists of:

- Global Header
- Workspace Header
- KPI Section
- Primary Visualization
- Secondary Visualization
- Analytical Table
- Supporting Information

---

## Information Hierarchy

Header

↓

Summary KPIs

↓

Primary Visualization

↓

Secondary Visualization

↓

Analytical Table

↓

Supporting Information

This hierarchy remains consistent across every workspace.

---

## Widget Prioritization

Priority order:

| Level | Component |
|---------|-----------|
| 1 | KPI Cards |
| 2 | Primary Chart |
| 3 | Secondary Chart |
| 4 | Analytical Table |
| 5 | Supporting Widgets |

Widgets shall not compete for visual priority.

---

## Composition Rules

Dashboards shall:

- answer one primary analytical question
- avoid redundant visualizations
- group related information
- preserve alignment
- minimize unnecessary scrolling

---

## Cross-Widget Consistency

Charts, tables, KPI cards, and filters shall:

- use shared Design Tokens
- share interaction patterns
- preserve terminology
- maintain visual consistency

---

## Responsive Behavior

Desktop

Multi-panel dashboard.

Tablet

Adaptive two-column layout.

Mobile

Single-column progressive layout.

Navigation hierarchy remains unchanged.

---

## Accessibility

Dashboards shall preserve:

- logical reading order
- semantic headings
- keyboard navigation
- screen reader compatibility

Target:

WCAG 2.2 AA

---

## Anti-Patterns

The following are prohibited:

- Decorative dashboards
- Duplicate visualizations
- Competing KPIs
- Hidden analytical context
- Inconsistent layouts

---

## Validation Checklist

- Dashboard hierarchy documented
- Widget prioritization documented
- Responsive behavior documented
- Accessibility documented

---

## Exit Criteria

P6-37 is complete when Dashboard Composition is approved and frozen.

---
# Workstream F — Responsive System

---

# P6-38 — Desktop Design Rules

## Purpose

This section defines the canonical Desktop Design Rules for the Decision Operating System.

Desktop is the primary analytical environment and serves as the reference implementation for all responsive adaptations.

Tablet and Mobile inherit the Desktop architecture while adapting presentation only.

---

## Objectives

Desktop layouts shall:

- maximize analytical efficiency
- support large datasets
- minimize unnecessary navigation
- preserve consistency
- provide the richest interaction model

---

## Target Environment

Desktop design targets:

- Standard desktop monitors
- Wide-screen monitors
- Multi-monitor workstations

The layout shall remain functional across supported viewport sizes.

---

## Canonical Layout

Every desktop workspace consists of:

- Global Header
- Persistent Sidebar
- Workspace Header
- Toolbar
- Primary Workspace
- Optional Secondary Panel
- Status Footer

---

## Layout Principles

Desktop layouts shall:

- maximize visible information
- minimize scrolling
- maintain alignment
- preserve hierarchy

---

## Navigation

Desktop navigation includes:

- Persistent Sidebar
- Global Header
- Breadcrumb
- Workspace Tabs
- Context Toolbar

Navigation remains visible whenever practical.

---

## Workspace Organization

Workspaces shall support:

- multi-column layouts
- side panels
- comparison views
- analytical dashboards

The Desktop experience is the reference for all downstream adaptations.

---

## Tables

Desktop tables may display:

- complete column sets
- advanced filtering
- multiple toolbars
- comparison features

No analytical capability shall be removed.

---

## Charts

Charts may use:

- full legends
- expanded tooltips
- comparison overlays
- advanced controls

Desktop provides the richest visualization experience.

---

## Accessibility

Desktop supports:

- keyboard navigation
- screen readers
- browser zoom
- reduced motion

Target:

WCAG 2.2 AA

---

## Anti-Patterns

The following are prohibited:

- unnecessary scrolling
- hidden navigation
- fragmented dashboards
- inconsistent workspace layouts

---

## Validation Checklist

- Desktop layout documented
- Navigation documented
- Workspace organization documented
- Accessibility documented

---

## Exit Criteria

P6-38 is complete when Desktop Design Rules are approved and frozen.

---

# P6-39 — Tablet Design Rules

## Purpose

This section defines the canonical Tablet Design Rules.

Tablet preserves Desktop workflows while adapting presentation for reduced screen width and touch interaction.

Tablet shall inherit Desktop architecture.

---

## Objectives

Tablet layouts shall:

- preserve analytical workflows
- optimize touch interaction
- reduce horizontal complexity
- maintain navigation consistency

---

## Target Environment

Tablet targets:

- landscape orientation
- portrait orientation
- keyboard-attached tablets
- touch-first interaction

---

## Canonical Layout

Every Tablet workspace consists of:

- Global Header
- Collapsible Sidebar
- Workspace Header
- Adaptive Toolbar
- Primary Workspace
- Optional Bottom Panel

---

## Navigation

Compared to Desktop:

| Desktop | Tablet |
|----------|---------|
| Persistent Sidebar | Collapsible Sidebar |
| Full Toolbar | Compact Toolbar |
| Multi-column | Reduced columns |

Navigation hierarchy remains unchanged.

---

## Dashboard Adaptation

Tablet dashboards shall:

- reduce simultaneous panels
- stack secondary widgets
- preserve KPI priority
- maintain analytical sequence

No dashboard functionality shall be removed.

---

## Tables

Tablet tables support:

- horizontal scrolling
- adaptive density
- prioritized columns
- responsive toolbars

Primary analytical columns remain visible.

---

## Charts

Charts shall:

- resize proportionally
- preserve aspect ratio
- simplify legends where necessary
- retain interaction behavior

---

## Touch Interaction

Tablet shall support:

- larger touch targets
- gesture interaction
- stylus compatibility
- optional keyboard navigation

---

## Accessibility

Tablet supports:

- keyboard navigation
- screen readers
- touch accessibility
- portrait and landscape orientation

Target:

WCAG 2.2 AA

---

## Anti-Patterns

The following are prohibited:

- separate Tablet navigation
- feature removal
- inconsistent interaction models
- hidden analytical content

---

## Validation Checklist

- Tablet layout documented
- Navigation documented
- Dashboard adaptation documented
- Accessibility documented

---

## Exit Criteria

P6-39 is complete when Tablet Design Rules are approved and frozen.

---

# P6-40 — Mobile Design Rules

## Purpose

This section defines the canonical Mobile Design Rules for the Decision Operating System.

Mobile provides complete analytical functionality while optimizing presentation for smaller screens and touch-first interaction.

Mobile adapts presentation only. Business logic, navigation hierarchy, and workflows remain identical to Desktop.

---

## Objectives

Mobile layouts shall:

- prioritize essential information
- optimize touch interaction
- preserve analytical workflows
- reduce cognitive load
- maintain consistency across devices

---

## Target Environment

Mobile design targets:

- Smartphones
- Foldable devices (phone mode)
- Touch-first interaction
- Portrait orientation (primary)
- Landscape orientation (supported)

---

## Canonical Layout

Every Mobile workspace consists of:

- Global Header
- Workspace Header
- Main Content
- Bottom Navigation
- Optional Floating Action Button
- Optional Bottom Sheet

---

## Navigation

Mobile navigation includes:

- Bottom Navigation
- Navigation Drawer
- Search Overlay
- Context Menu

Navigation hierarchy shall remain identical to Desktop.

---

## Dashboard Adaptation

Mobile dashboards shall:

- use a single-column layout
- stack KPI cards vertically
- collapse secondary sections
- preserve analytical priority
- avoid horizontal scrolling where practical

Users shall still have access to the same analytical information.

---

## Tables

Large analytical tables shall adapt using one or more of:

- Responsive Cards
- Prioritized Columns
- Expandable Rows
- Horizontal Scrolling (when unavoidable)

No data shall become inaccessible because of screen size.

---

## Charts

Charts shall:

- scale proportionally
- support touch inspection
- simplify legends when necessary
- preserve analytical meaning

Interactive behavior remains consistent with larger devices.

---

## Forms

Mobile forms shall:

- use full-width controls
- stack fields vertically
- optimize touch targets
- reduce unnecessary scrolling

Validation behavior remains identical across devices.

---

## Touch Interaction

Touch targets shall:

- remain comfortably selectable
- provide immediate feedback
- avoid accidental activation
- preserve spacing between controls

Gestures shall supplement, not replace, visible controls.

---

## Accessibility

Mobile supports:

- screen readers
- scalable text
- reduced motion
- touch accessibility
- high-contrast themes

Target:

WCAG 2.2 AA

---

## Anti-Patterns

The following are prohibited:

- Hidden functionality
- Mobile-only business rules
- Different terminology
- Different navigation hierarchy
- Unreachable controls

---

## Validation Checklist

- Mobile layout documented
- Navigation documented
- Dashboard adaptation documented
- Touch interaction documented
- Accessibility documented

---

## Exit Criteria

P6-40 is complete when Mobile Design Rules are approved and frozen.

---

# P6-41 — Adaptive Components

## Purpose

This section defines how reusable components adapt across Desktop, Tablet, and Mobile while preserving identical functionality.

Adaptive Components modify presentation only.

Semantic meaning, interaction logic, and business behavior remain unchanged.

---

## Objectives

Adaptive Components shall:

- preserve consistency
- maintain usability
- optimize available space
- support every supported device
- eliminate duplicate implementations

---

## Adaptation Philosophy

Components shall:

- retain semantic identity
- preserve interaction patterns
- maintain accessibility
- adapt layout only

The Design System follows a "single component, multiple presentations" philosophy.

---

## Adaptation Matrix

| Component | Desktop | Tablet | Mobile |
|-----------|----------|---------|---------|
| Sidebar | Persistent | Collapsible | Drawer |
| Toolbar | Full | Compact | Overflow |
| Table | Full Grid | Scrollable | Responsive Cards |
| KPI Cards | Multi-column | Reduced Columns | Single Column |
| Charts | Full Controls | Simplified Controls | Touch Optimized |
| Dialog | Modal | Responsive Modal | Bottom Sheet / Full Screen |

---

## Layout Adaptation

Presentation adapts progressively:

Desktop

↓

Tablet

↓

Mobile

Layout changes shall never alter business workflows.

---

## Interaction Consistency

Across every supported device:

- navigation remains identical
- terminology remains identical
- workflows remain identical
- validation remains identical

Only presentation adapts.

---

## Responsive Principles

Adaptive Components shall:

- avoid layout shifts
- preserve alignment
- maintain hierarchy
- optimize available space

Responsive behavior shall remain predictable.

---

## Performance

Adaptive Components shall:

- minimize re-rendering
- reduce layout recalculation
- preserve interaction responsiveness
- support efficient rendering

---

## Accessibility

Adaptive Components preserve:

- keyboard navigation (where applicable)
- touch accessibility
- screen reader compatibility
- semantic structure
- focus management

Target:

WCAG 2.2 AA

---

## Anti-Patterns

The following are prohibited:

- Device-specific business logic
- Duplicate component implementations
- Different navigation models
- Feature removal on Mobile
- Different terminology across devices

---

## Governance

Adaptive behavior shall be maintained centrally within the Design System.

Device-specific component forks are prohibited unless approved through the formal Architecture Decision Record (ADR) process.

---

## Validation Checklist

- Adaptation philosophy documented
- Adaptation matrix documented
- Interaction consistency documented
- Accessibility documented
- Governance documented

---

## Exit Criteria

P6-41 is complete when Adaptive Components are approved and frozen.

---

# Workstream G — Accessibility

---

# P6-42 — Accessibility Standards

## Purpose

This section defines the overarching Accessibility Standards for the Decision Operating System.

Accessibility is a core architectural requirement of the Design System and shall be incorporated into every component from the beginning of the design process.

Accessibility shall never be treated as a post-implementation enhancement.

---

## Objectives

The Accessibility Standards shall:

- support inclusive design
- ensure consistent accessibility
- reduce usability barriers
- comply with international standards
- integrate into every reusable component

---

## Compliance Target

The Design System targets:

**WCAG 2.2 Level AA**

Future versions may adopt AAA requirements where practical.

---

## Accessibility Principles

The Design System follows four fundamental principles:

- Perceivable
- Operable
- Understandable
- Robust

Every component shall satisfy these principles.

---

## Accessibility Scope

Accessibility requirements apply to:

- Navigation
- Forms
- Tables
- Charts
- Dialogs
- Notifications
- Responsive layouts
- Keyboard interaction
- Screen readers
- Color usage

Accessibility applies equally across Desktop, Tablet, and Mobile.

---

## Inclusive Design

Interfaces shall accommodate users with:

- visual impairments
- motor impairments
- hearing impairments
- cognitive impairments
- temporary disabilities
- situational limitations

---

## Component Requirements

Every reusable component shall provide:

- accessible labels
- logical focus order
- keyboard operation
- screen reader compatibility
- sufficient color contrast

No shared component is exempt.

---

## Responsive Accessibility

Accessibility behavior shall remain identical across:

- Desktop
- Tablet
- Mobile

Presentation may adapt.

Accessibility shall not.

---

## Testing Requirements

Accessibility verification shall include:

- keyboard testing
- screen reader testing
- color contrast verification
- responsive testing
- focus management verification

Testing shall occur before release.

---

## Governance

Accessibility regressions are considered architectural defects.

Every Design System release shall include accessibility validation.

---

## Validation Checklist

- Accessibility principles documented
- Compliance target documented
- Component requirements documented
- Testing requirements documented
- Governance documented

---

## Exit Criteria

P6-42 is complete when Accessibility Standards are approved and frozen.

---

# P6-43 — Keyboard Interaction System

## Purpose

This section defines the canonical Keyboard Interaction System.

Every workflow within the Decision Operating System shall be fully operable using a keyboard.

Keyboard interaction is a first-class interaction model.

---

## Objectives

The Keyboard Interaction System shall:

- support complete application use
- reduce dependence on pointing devices
- remain predictable
- preserve accessibility
- remain consistent

---

## Navigation Keys

The standard keyboard navigation model includes:

| Key | Function |
|------|----------|
| Tab | Next interactive element |
| Shift + Tab | Previous interactive element |
| Enter | Activate |
| Space | Toggle / Activate |
| Escape | Close overlay |
| Home | First item |
| End | Last item |
| Page Up | Previous page |
| Page Down | Next page |

Platform conventions shall be preserved where applicable.

---

## Directional Navigation

Arrow keys are used within structured components.

Supported components include:

- Menus
- Dropdowns
- Tabs
- Tables
- Grids
- Tree Views

Directional behavior shall remain consistent across components.

---

## Focus Management

Focus shall:

- remain visible
- follow logical reading order
- never disappear
- restore appropriately after temporary overlays

Focus indicators shall never rely solely on color.

---

## Focus Trapping

Dialogs, drawers, and other modal interfaces shall:

- trap focus
- cycle focus internally
- restore focus when closed

Only one active focus trap may exist at a time.

---

## Keyboard Shortcuts

Recommended application shortcuts include:

| Shortcut | Action |
|----------|--------|
| Ctrl/Cmd + K | Global Search |
| Ctrl/Cmd + F | Workspace Search |
| Ctrl/Cmd + R | Refresh Workspace |
| Escape | Close Active Overlay |

Additional shortcuts shall avoid conflicts with operating system conventions.

---

## Component Requirements

Every interactive component shall support:

- keyboard activation
- visible focus
- logical traversal
- accessible state changes

Mouse-only interaction is prohibited.

---

## Accessibility

Keyboard interaction shall satisfy:

- WCAG 2.2 AA
- logical focus order
- visible focus indicators
- predictable navigation

---

## Anti-Patterns

The following are prohibited:

- Keyboard traps
- Invisible focus
- Mouse-only controls
- Inconsistent keyboard behavior
- Unreachable interface elements

---

## Validation Checklist

- Navigation keys documented
- Focus management documented
- Keyboard shortcuts documented
- Accessibility documented

---

## Exit Criteria

P6-43 is complete when the Keyboard Interaction System is approved and frozen.

---

# P6-44 — Screen Reader Standards

## Purpose

This section defines the canonical Screen Reader Standards for the Decision Operating System.

Every reusable component shall expose sufficient semantic information to enable accurate interpretation by assistive technologies.

Screen reader compatibility is a mandatory Design System requirement.

---

## Objectives

Screen Reader Standards shall:

- preserve application structure
- expose semantic meaning
- support efficient navigation
- provide accessible feedback
- remain consistent across all components

---

## Semantic Structure

Every page shall expose semantic landmarks.

Required landmarks include:

- Header
- Navigation
- Main
- Optional Aside
- Footer

Exactly one Main region shall exist per page.

---

## Heading Hierarchy

Heading structure shall follow a logical hierarchy.

Requirements:

- One H1 per page
- Sequential heading levels
- No skipped heading levels without justification
- Headings shall describe content accurately

---

## Accessible Names

Every interactive element shall expose an accessible name.

Examples include:

- Buttons
- Links
- Inputs
- Tabs
- Menus
- Toolbar actions
- Icons used as controls

Decorative graphics shall remain hidden from assistive technologies.

---

## Form Accessibility

Every form shall provide:

- associated labels
- validation announcements
- required field indication
- error descriptions
- logical tab order

Placeholder text shall never replace labels.

---

## Dynamic Content

Dynamic interface updates shall announce meaningful changes.

Examples include:

- Notifications
- Validation results
- Progress updates
- Loading completion
- Successful operations

Announcements shall avoid unnecessary repetition.

---

## Tables

Tables shall expose:

- header relationships
- row relationships
- sorting state
- selection state
- pagination information

Large analytical tables shall remain navigable.

---

## Charts

Charts shall provide:

- descriptive titles
- textual summaries
- accessible legends
- alternative descriptions where appropriate

Charts shall never rely solely on visual interpretation.

---

## Dialogs & Drawers

Dialogs and Drawers shall:

- announce opening
- expose titles
- announce closing
- restore focus correctly

---

## Navigation

Navigation components shall expose:

- landmarks
- current page
- expanded state
- selected state
- navigation hierarchy

---

## Accessibility

The complete Screen Reader architecture targets:

WCAG 2.2 AA

Screen Reader compatibility shall remain identical across:

- Desktop
- Tablet
- Mobile

---

## Anti-Patterns

The following are prohibited:

- Missing labels
- Missing headings
- Decorative content announced unnecessarily
- Unannounced dynamic updates
- Hidden navigation context

---

## Validation Checklist

- Landmark structure documented
- Heading hierarchy documented
- Accessible names documented
- Dynamic announcements documented
- Table support documented
- Chart support documented

---

## Exit Criteria

P6-44 is complete when Screen Reader Standards are approved and frozen.

---

# P6-45 — Color Contrast & WCAG

## Purpose

This section defines the visual accessibility requirements governing color usage, contrast, and compliance with WCAG.

These requirements ensure the interface remains readable, distinguishable, and usable across supported environments.

---

## Objectives

The Color & Contrast system shall:

- maximize readability
- preserve semantic meaning
- support accessibility
- remain theme-independent
- prevent ambiguity

---

## Compliance Target

Minimum compliance target:

WCAG 2.2 Level AA

Future releases may target AAA where practical.

---

## Color Philosophy

Color communicates semantic meaning.

Color shall reinforce information rather than become the sole source of meaning.

---

## Contrast Requirements

The following interface elements shall satisfy the project's accessibility requirements:

- Body text
- Headings
- Buttons
- Form controls
- Navigation
- Tables
- Charts
- Icons used as controls

Actual contrast values are governed by the Design Tokens.

---

## Color Independence

Information shall never rely solely on color.

Every status indicator shall include one or more additional cues:

- Text
- Icon
- Pattern
- Shape

Examples:

✔ Success icon + label

✔ Warning icon + text

✘ Green color only

---

## Focus Indicators

Focus indicators shall:

- remain clearly visible
- remain consistent
- satisfy accessibility requirements

Focus shall never rely solely on color.

---

## Theme Compatibility

Both supported themes shall:

- preserve semantic meaning
- satisfy accessibility requirements
- maintain consistent interaction behavior

Theme switching shall not reduce accessibility.

---

## Charts & Data Visualization

Charts shall:

- avoid color-only interpretation
- provide legends
- provide labels where appropriate
- preserve sufficient contrast

Heatmaps shall include legends and textual interpretation.

---

## Verification

Accessibility verification shall include:

- contrast validation
- keyboard focus inspection
- theme verification
- chart inspection
- table inspection
- responsive verification

Verification is required before release.

---

## Governance

Any Design Token modification affecting accessibility requires Design System review.

Accessibility regressions shall be treated as architectural defects.

---

## Anti-Patterns

The following are prohibited:

- Low-contrast text
- Invisible focus indicators
- Color-only communication
- Theme-specific accessibility regressions
- Decorative color changes that obscure meaning

---

## Validation Checklist

- Compliance target documented
- Contrast requirements documented
- Color independence documented
- Theme compatibility documented
- Verification documented
- Governance documented

---

## Exit Criteria

P6-45 is complete when Color Contrast & WCAG requirements are approved and frozen.

---

# Workstream H — Governance

---

# P6-46 — Component Naming Standards

## Purpose

This section defines the canonical naming conventions used throughout the Design System.

Consistent naming improves communication between Design, Product, and Engineering while simplifying implementation and long-term maintenance.

Every reusable component shall follow these standards.

---

## Objectives

Component naming shall:

- remain consistent
- be predictable
- avoid ambiguity
- scale as the Design System grows
- align with implementation terminology

---

## Naming Principles

Component names shall be:

- descriptive
- concise
- reusable
- implementation-independent

Names shall describe purpose rather than appearance.

---

## Naming Structure

Recommended hierarchy:

Component

↓

Variant

↓

Modifier

↓

State

Example:

Button

↓

Primary

↓

Large

↓

Disabled

---

## Component Categories

The Design System groups components into:

- Navigation
- Inputs
- Data Display
- Feedback
- Overlays
- Layout
- Visualization

Each component belongs to exactly one primary category.

---

## Variant Naming

Variants describe functional differences rather than styling.

Examples:

Primary Button

Secondary Button

Success Notification

Error Notification

Modal Dialog

Navigation Drawer

---

## State Naming

Standard component states include:

- Default
- Hover
- Focus
- Active
- Disabled
- Loading
- Error
- Success

State names remain identical across all reusable components.

---

## Token Alignment

Component names shall align with Design Token naming.

Example:

Button.Primary.Background

↓

button.primary.background

This alignment simplifies implementation and maintenance.

---

## Documentation

Each reusable component shall document:

- Name
- Purpose
- Category
- Variants
- States
- Accessibility
- Responsive behavior

Documentation shall remain synchronized with implementation.

---

## Governance

New component names require Design System review.

Renaming existing public components requires:

- architectural review
- migration documentation
- version update

---

## Anti-Patterns

The following are prohibited:

- Visual-only names
- Duplicate names
- Abbreviations without documentation
- Inconsistent state names
- Component aliases

---

## Validation Checklist

- Naming principles documented
- Categories documented
- Variant naming documented
- State naming documented
- Governance documented

---

## Exit Criteria

P6-46 is complete when Component Naming Standards are approved and frozen.

---

# P6-47 — Figma Organization

## Purpose

This section defines the canonical organization of the Design System within Figma.

The Figma workspace shall mirror the architecture of this Design System specification to maintain consistency between documentation and implementation.

---

## Objectives

The Figma organization shall:

- remain predictable
- simplify navigation
- reduce duplication
- support collaboration
- scale with future releases

---

## Workspace Structure

The Design System library shall be organized into the following top-level sections:

- Foundations
- Tokens
- Components
- Patterns
- Templates
- Documentation

Every design artifact shall belong to one primary section.

---

## Foundations

The Foundations section contains:

- Design Principles
- Visual Language
- Color System
- Typography
- Spacing
- Elevation
- Motion

These assets define the visual foundation of the Design System.

---

## Tokens

The Tokens section contains:

- Color Tokens
- Typography Tokens
- Spacing Tokens
- Radius Tokens
- Border Tokens
- Elevation Tokens
- Motion Tokens
- Theme Tokens

Token names shall match the naming conventions defined in P6-46.

---

## Components

Reusable components shall be grouped into logical categories:

- Navigation
- Inputs
- Buttons
- Cards
- Tables
- Charts
- Feedback
- Overlays

Each component page shall include:

- Variants
- States
- Responsive behavior
- Accessibility notes

---

## Patterns

The Patterns section contains reusable compositions such as:

- Dashboard layouts
- Forms
- Tables
- Search workflows
- Empty states
- Error states

Patterns combine components without redefining them.

---

## Templates

Templates provide complete page compositions for common workflows.

Examples include:

- Dashboard
- Portfolio
- Watchlist
- Decision Workspace
- Settings

Templates are implementation references rather than reusable components.

---

## Documentation

Every major library section shall include:

- Purpose
- Usage guidance
- Component ownership
- Version information
- Related documentation

Documentation shall remain synchronized with this specification.

---

## Library Governance

The Design System library shall:

- maintain a single source of truth
- avoid duplicated components
- archive deprecated assets
- document breaking changes

Shared components shall not be modified directly within product files.

---

## Versioning

Each published library release shall include:

- Version number
- Release date
- Change summary
- Migration notes (if required)

Library releases shall align with the Design System version defined in this document.

---

## Collaboration Guidelines

Design contributors shall:

- reuse existing components
- avoid local overrides
- propose changes through Design System governance
- document new patterns before publication

---

## Validation Checklist

- Workspace structure documented
- Library organization documented
- Governance documented
- Versioning documented
- Collaboration guidelines documented

---

## Exit Criteria

P6-47 is complete when the Figma Organization has been approved and frozen.

---

# P6-48 — Versioning & Change Control

## Purpose

This section defines the governance process for evolving the Decision Operating System Design System after its initial release.

The objective is to ensure that every modification remains controlled, traceable, and compatible with the architectural baseline established in Phases 4–6.

---

## Objectives

Versioning & Change Control shall:

- preserve Design System stability
- prevent uncontrolled design drift
- maintain backward compatibility where practical
- ensure traceability
- support long-term evolution

---

## Scope

This governance applies to:

- Design Tokens
- Shared Components
- Patterns
- Templates
- Responsive Rules
- Accessibility Standards
- Documentation
- Figma Library

Every published Design System artifact follows this process.

---

## Versioning Strategy

The Design System follows Semantic Versioning.

| Version | Meaning |
|----------|----------|
| Major | Breaking architectural change |
| Minor | Backward-compatible enhancement |
| Patch | Documentation, accessibility, or implementation correction |

Examples:

v1.0.0

↓

v1.1.0

↓

v1.1.1

---

## Change Categories

Every proposed change belongs to one category.

| Category | Approval Required |
|----------|-------------------|
| New Component | Yes |
| Component Removal | Yes |
| Component Rename | Yes |
| Token Modification | Yes |
| Accessibility Change | Yes |
| Responsive Architecture | Yes |
| Documentation Correction | No (Editorial) |
| Typographical Fix | No |

---

## Change Workflow

Every architectural change follows the same lifecycle.

Proposal

↓

Design Review

↓

Architecture Review

↓

Approval

↓

Implementation

↓

Validation

↓

Documentation Update

↓

Release

No architectural change bypasses this workflow.

---

## Approval Responsibilities

| Role | Responsibility |
|------|----------------|
| Product | User impact |
| UX | Experience consistency |
| UI | Visual consistency |
| Engineering | Technical feasibility |
| Architecture | System integrity |

Approval is required before implementation.

---

## Deprecation Policy

Deprecated assets shall:

- remain documented
- identify replacement guidance
- record deprecation version
- remain available until the next major release unless exceptional circumstances require earlier removal

---

## Release Documentation

Every release shall include:

- Version Number
- Release Date
- Summary
- Changed Components
- Changed Tokens
- Migration Guidance (if applicable)

Release documentation becomes part of the permanent project record.

---

## Audit Requirements

Every release shall verify:

- component consistency
- token consistency
- accessibility compliance
- responsive behavior
- documentation completeness

Release approval shall not occur without audit completion.

---

## Validation Checklist

- Versioning documented
- Approval workflow documented
- Deprecation policy documented
- Release documentation documented
- Audit requirements documented

---

## Exit Criteria

P6-48 is complete when Versioning & Change Control is approved and frozen.

---

# P6-49 — Design System Audit

## Purpose

This section performs the final architectural audit of the Phase 6 Design System.

The audit confirms completeness, consistency, accessibility, governance, and readiness for implementation.

No new functionality is introduced during this audit.

---

## Audit Scope

The following areas are reviewed:

- Design Foundations
- Design Tokens
- Core Components
- Advanced Components
- Data Visualization
- Responsive System
- Accessibility
- Governance

---

## Design Foundation Audit

| Area | Result |
|------|--------|
| Design Principles | PASS |
| Visual Language | PASS |
| Color System | PASS |
| Typography | PASS |
| Spacing | PASS |
| Elevation | PASS |
| Motion | PASS |

Overall Result:

PASS

---

## Token Audit

Verified:

- Color Tokens
- Typography Tokens
- Spacing Tokens
- Radius Tokens
- Border Tokens
- Theme Tokens

Overall Result:

PASS

---

## Component Audit

Verified Components:

- Buttons
- Inputs
- Dropdowns
- Tables
- Cards
- Charts
- Tabs
- Breadcrumbs
- Toolbars
- Navigation
- Dialogs
- Drawers
- Notifications
- Toasts
- Progress Indicators
- Empty States
- Error States
- Loading Skeletons

Overall Result:

PASS

---

## Responsive Audit

Verified:

- Desktop Rules
- Tablet Rules
- Mobile Rules
- Adaptive Components

Overall Result:

PASS

---

## Accessibility Audit

Verified:

- Accessibility Standards
- Keyboard Navigation
- Screen Reader Support
- WCAG Compliance

Overall Result:

PASS

---

## Governance Audit

Verified:

- Naming Standards
- Figma Organization
- Versioning
- Change Control

Overall Result:

PASS

---

## Engineering Readiness

The Design System provides:

- reusable components
- token architecture
- accessibility architecture
- responsive rules
- governance model

Implementation Readiness:

READY

---

## Audit Summary

| Area | Result |
|------|--------|
| Foundations | PASS |
| Tokens | PASS |
| Components | PASS |
| Visualization | PASS |
| Responsive | PASS |
| Accessibility | PASS |
| Governance | PASS |

Overall Assessment:

READY FOR IMPLEMENTATION

---

## Validation Checklist

- All workstreams audited
- Consistency verified
- Accessibility verified
- Responsive behavior verified
- Governance verified

---

## Exit Criteria

P6-49 is complete when the Design System Audit is approved.

---

# P6-50 — Final Freeze

## Purpose

This section formally freezes Phase 6 and establishes the Design System as the canonical visual specification for frontend implementation.

After this point, architectural modifications require formal governance approval.

---

## Deliverables

Phase 6 produces the following approved deliverables:

- Design Foundations
- Visual Language
- Color System
- Typography System
- Spacing System
- Elevation Model
- Motion Principles
- Design Tokens
- Core Components
- Advanced Components
- Data Visualization Standards
- Responsive Rules
- Accessibility Standards
- Governance Framework

Together, these artifacts constitute the complete Design System.

---

## Downstream Dependencies

The frozen Design System becomes the required input for:

| Phase | Purpose |
|------|----------|
| Phase 7 | Frontend Technical Architecture |
| Phase 8 | Frontend Engineering Planning |
| Phase 9 | Frontend Implementation |

No downstream phase may redefine Design System architecture.

---

## Freeze Checklist

| Requirement | Status |
|-------------|--------|
| Design Foundations | ✅ Complete |
| Design Tokens | ✅ Complete |
| Core Components | ✅ Complete |
| Advanced Components | ✅ Complete |
| Data Visualization | ✅ Complete |
| Responsive System | ✅ Complete |
| Accessibility | ✅ Complete |
| Governance | ✅ Complete |
| Documentation | ✅ Complete |

Overall Status:

READY FOR FREEZE

---

## Post-Freeze Change Policy

Following the freeze:

The following require formal approval:

- New component categories
- Token architecture modifications
- Responsive architecture changes
- Accessibility architecture changes
- Navigation architecture changes

Editorial corrections may proceed through the normal documentation process.

---

## Canonical Document

Document Name:

PHASE_6_DESIGN_SYSTEM_v1.0.md

Version:

v1.0.0

Status:

FROZEN

This document becomes the authoritative Design System specification for the Decision Operating System.

---

## Approval Matrix

| Area | Status |
|------|--------|
| Product Architecture | Approved |
| UX Architecture | Approved |
| UI Architecture | Approved |
| Frontend Architecture | Approved |
| Engineering Governance | Approved |

Overall Decision:

GO FOR PHASE 7

---

## Phase 6 Completion Summary

The Design System now provides:

- Unified visual language
- Standardized design tokens
- Reusable component library
- Responsive architecture
- Accessibility standards
- Governance model
- Implementation-ready specifications

Phase 6 is complete.

---

# Appendix A — Design Principles Summary

# Appendix A — Design Principles Summary

## Purpose

This appendix summarizes the core design principles established throughout Phase 6.

These principles govern every visual decision within the Decision Operating System.

---

## Core Principles

| Principle | Summary |
|-----------|---------|
| Information First | Data has priority over decoration. |
| Consistency Before Creativity | Similar interactions behave identically. |
| Recognition Over Recall | Interfaces minimize memory load. |
| Progressive Disclosure | Reveal complexity gradually. |
| Functional Whitespace | Space communicates structure. |
| Predictable Interaction | Every action behaves consistently. |
| Accessibility by Default | Accessibility is mandatory. |
| Responsive by Design | Layout adapts while behavior remains consistent. |

---

## Design Goals

The Design System prioritizes:

- Clarity
- Consistency
- Readability
- Analytical efficiency
- Trust
- Scalability

---

## Design Constraints

The following are prohibited:

- Decorative interfaces
- Hidden navigation
- Inconsistent interactions
- Duplicate components
- Color-only communication
- Device-specific workflows

---

# Appendix B — Color Architecture

## Purpose

This appendix summarizes the semantic color architecture.

---

## Semantic Categories

- Primary
- Secondary
- Neutral
- Success
- Warning
- Danger
- Information

---

## Functional Categories

- Background
- Surface
- Border
- Text
- Interactive
- Feedback
- Charts

---

## Theme Support

Supported themes:

- Light
- Dark

Future themes inherit the same semantic structure.

---

## Accessibility

The color system supports:

- WCAG 2.2 AA
- Color independence
- Visible focus
- Semantic consistency

---

# Appendix C — Typography Scale

## Typography Hierarchy

| Level | Purpose |
|---------|----------|
| Display | Landing pages |
| H1 | Workspace title |
| H2 | Section title |
| H3 | Card title |
| H4 | Subsection |
| Body | General content |
| Caption | Supporting text |
| Label | Controls |
| Code | Technical values |

---

## Typography Principles

Typography shall remain:

- Readable
- Consistent
- Accessible
- Scannable

---

## Alignment Rules

- Left alignment by default
- Right alignment for numerical values
- Center alignment only for limited scenarios

---

# Appendix D — Spacing Scale

## Spacing Tokens

The Design System defines the following logical spacing tokens:

- XS
- S
- M
- L
- XL
- 2XL

---

## Usage

Spacing Tokens govern:

- Margin
- Padding
- Gap
- Grid spacing
- Section spacing
- Component spacing

---

## Grid Hierarchy

Page

↓

Workspace

↓

Section

↓

Component

↓

Element

---

# Appendix E — Design Token Registry

## Token Categories

The Design System includes the following token families:

- Color Tokens
- Typography Tokens
- Spacing Tokens
- Radius Tokens
- Border Tokens
- Elevation Tokens
- Motion Tokens
- Theme Tokens
- Icon Tokens

---

## Token Hierarchy

Core Tokens

↓

Semantic Tokens

↓

Component Tokens

---

## Governance

All Design Tokens are governed centrally.

Hard-coded visual values are prohibited.

---

# Appendix F — Component Inventory

## Core Components

- Buttons
- Inputs
- Dropdowns
- Tables
- Cards
- Charts
- Tabs
- Breadcrumbs
- Toolbars
- Navigation Components

---

## Advanced Components

- Dialogs
- Drawers
- Notifications
- Toasts
- Progress Indicators
- Empty States
- Error States
- Loading Skeletons

---

## Data Visualization

- KPI Cards
- Analytical Tables
- Heatmaps
- Dashboards

---

## Responsive Components

- Desktop Layout
- Tablet Layout
- Mobile Layout
- Adaptive Components

---

## Accessibility Components

- Keyboard Navigation
- Screen Reader Support
- Focus Management
- Accessible Color System

---

## Governance Components

- Naming Standards
- Figma Organization
- Version Control
- Design System Audit

# Appendix G — Component State Matrix

## Purpose

This appendix summarizes the standard interaction states supported across reusable components.

All interactive components shall implement these states consistently.

---

## Standard Component States

| State | Description |
|--------|-------------|
| Default | Initial presentation |
| Hover | Pointer interaction |
| Focus | Keyboard interaction |
| Active | User activation |
| Selected | Current selection |
| Disabled | Unavailable for interaction |
| Loading | Processing state |
| Success | Positive outcome |
| Warning | Caution state |
| Error | Failure state |

---

## Component Coverage

| Component | Required States |
|-----------|-----------------|
| Button | Default, Hover, Focus, Active, Disabled, Loading |
| Input | Default, Focus, Filled, Error, Disabled |
| Dropdown | Closed, Open, Hover, Focus, Disabled |
| Table | Hover, Selected, Focus |
| Card | Default, Hover (optional), Selected (optional) |
| Dialog | Open, Closing |
| Notification | Visible, Dismissed |
| Toast | Visible, Auto-dismissed |
| Progress Indicator | Idle, Active, Complete, Failed |

---

# Appendix H — Responsive Adaptation Matrix

## Purpose

This appendix summarizes responsive behavior across supported devices.

---

## Device Matrix

| Component | Desktop | Tablet | Mobile |
|-----------|----------|---------|---------|
| Sidebar | Persistent | Collapsible | Drawer |
| Header | Persistent | Persistent | Persistent |
| Toolbar | Full | Compact | Overflow |
| Tables | Full Grid | Scrollable | Responsive Cards |
| KPI Cards | Multi-column | Reduced Columns | Single Column |
| Charts | Full Controls | Adaptive | Simplified |
| Dialogs | Modal | Responsive Modal | Bottom Sheet |
| Navigation | Sidebar | Sidebar | Bottom Navigation |

---

## Responsive Principles

Responsive adaptation shall preserve:

- Business logic
- Navigation hierarchy
- Terminology
- Accessibility
- Interaction model

Only presentation may change.

---

# Appendix I — Accessibility Compliance Matrix

## Accessibility Standards

| Area | Standard |
|------|----------|
| Keyboard Navigation | WCAG 2.2 AA |
| Screen Reader Support | WCAG 2.2 AA |
| Color Contrast | WCAG 2.2 AA |
| Focus Visibility | WCAG 2.2 AA |
| Responsive Accessibility | WCAG 2.2 AA |
| Forms | WCAG 2.2 AA |
| Tables | WCAG 2.2 AA |
| Charts | WCAG 2.2 AA |

---

## Accessibility Checklist

The Design System requires:

- Semantic HTML
- Logical heading hierarchy
- Keyboard operability
- Focus management
- Screen reader compatibility
- Accessible names
- Accessible error messaging
- Color-independent communication

Accessibility is mandatory for every reusable component.

---

# Appendix J — Version History

## Initial Release

| Version | Status | Description |
|----------|--------|-------------|
| 1.0.0 | FROZEN | Initial Design System release |

---

## Future Releases

Future releases shall follow Semantic Versioning.

| Version | Purpose |
|----------|---------|
| Major | Breaking architectural changes |
| Minor | New functionality |
| Patch | Documentation or implementation corrections |

---

## Change Management

Every release shall include:

- Version Number
- Release Date
- Summary of Changes
- Migration Guidance (if applicable)
- Approval Record

---

# Appendix K — Governance Workflow

## Design System Lifecycle

Every Design System modification follows the same governance process.

```text
Proposal
    │
    ▼
Design Review
    │
    ▼
Architecture Review
    │
    ▼
Approval
    │
    ▼
Implementation
    │
    ▼
Validation
    │
    ▼
Documentation Update
    │
    ▼
Release
```

---

## Governance Principles

The Design System shall remain:

- Stable
- Predictable
- Traceable
- Backward compatible where practical
- Fully documented

Architectural modifications require formal approval.

Editorial corrections may proceed through the documentation process.

---

# Final Phase Summary

## Deliverables

Phase 6 delivers the complete Design System for the Decision Operating System, including:

- Design Foundations
- Visual Language
- Color System
- Typography System
- Spacing System
- Elevation Model
- Motion Principles
- Design Tokens
- Core Component Library
- Advanced Component Library
- Data Visualization Standards
- Responsive Design Rules
- Accessibility Standards
- Governance Framework

---

## Dependencies

This document depends on:

- PHASE_4_UX_BLUEPRINT_v1.0.md
- PHASE_5_WIREFRAMES_v1.0.md

This document serves as the architectural input for:

- PHASE_7_FRONTEND_TECHNICAL_ARCHITECTURE_v1.0.md
- PHASE_8_FRONTEND_ENGINEERING_PLAN_v1.0.md
- PHASE_9_FRONTEND_IMPLEMENTATION_v1.0.md

---

## Final Freeze Statement

Document:

PHASE_6_DESIGN_SYSTEM_v1.0.md

Version:

v1.0.0

Status:

**FROZEN**

The Design System defined in this document is the canonical visual specification for the Decision Operating System.

All frontend implementation shall conform to this specification unless superseded through the formal Design System governance and versioning process.

---

# End of Document









