---
name: LendIQ
colors:
  surface: '#fff8f7'
  surface-dim: '#efd4d2'
  surface-bright: '#fff8f7'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#fff0ef'
  surface-container: '#ffe9e7'
  surface-container-high: '#fde2e0'
  surface-container-highest: '#f7dcdb'
  on-surface: '#261817'
  on-surface-variant: '#5a403f'
  inverse-surface: '#3d2c2c'
  inverse-on-surface: '#ffedeb'
  outline: '#8e706f'
  outline-variant: '#e2bebc'
  surface-tint: '#b52330'
  primary: '#b52330'
  on-primary: '#ffffff'
  primary-container: '#ff5a5f'
  on-primary-container: '#61000e'
  inverse-primary: '#ffb3b0'
  secondary: '#555f6f'
  on-secondary: '#ffffff'
  secondary-container: '#d6e0f3'
  on-secondary-container: '#596373'
  tertiary: '#006c4c'
  on-tertiary: '#ffffff'
  tertiary-container: '#00a879'
  on-tertiary-container: '#003423'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#ffdad8'
  primary-fixed-dim: '#ffb3b0'
  on-primary-fixed: '#410007'
  on-primary-fixed-variant: '#92001b'
  secondary-fixed: '#d9e3f6'
  secondary-fixed-dim: '#bdc7d9'
  on-secondary-fixed: '#121c2a'
  on-secondary-fixed-variant: '#3d4756'
  tertiary-fixed: '#78fac4'
  tertiary-fixed-dim: '#59ddaa'
  on-tertiary-fixed: '#002115'
  on-tertiary-fixed-variant: '#005139'
  background: '#fff8f7'
  on-background: '#261817'
  surface-variant: '#f7dcdb'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 44px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  metric-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 4px
  gap-xs: 4px
  gap-sm: 8px
  gap-md: 16px
  gap-lg: 24px
  container-padding: 24px
  margin-mobile: 16px
  margin-desktop: 32px
  sidebar-width: 260px
---

## Brand & Style
The design system focuses on high-trust, data-intensive fintech operations for emerging markets. The brand personality is authoritative yet accessible, balancing professional precision with the modern energy of the fintech sector. 

The visual style is **Corporate Modern**, characterized by a high-clarity interface that prioritizes data legibility and systematic organization. It utilizes a clean "card-on-canvas" approach where information is compartmentalized into discrete, white modules to reduce cognitive load. The aesthetic is inspired by high-end dashboard interfaces, emphasizing breathable white space, crisp borders, and subtle depth to create a sense of reliability and technical sophistication.

## Colors
The palette is built around **LendIQ Red**, a high-energy primary color used strategically for calls to action, brand presence, and critical highlights. This is balanced by **Dark Navy**, which provides the grounding necessary for professional financial applications, used primarily for navigation backgrounds and primary text.

The interface utilizes a light-mode-only strategy with a neutral **Light Grey** background to separate the surface of the application from the content cards. Semantic colors for success and danger are chosen for high visibility against white backgrounds to ensure risk indicators are unmistakable.

## Typography
The system uses **Inter** (as the closest high-quality equivalent to SF Pro Display) to provide a neutral, systematic, and highly legible experience across all densities. 

Key metrics and financial figures use the `metric-lg` style with bold weights and tight letter spacing to command attention. Labels for data tables and small descriptors use uppercase styling with increased tracking to ensure clarity at small scales. Heading levels scale down on mobile devices to preserve screen real estate while maintaining a clear hierarchy.

## Layout & Spacing
The layout follows a **Fixed Grid** approach for internal card content and a **Fluid Grid** for the overall dashboard orchestration. On desktop, the interface is anchored by a persistent left sidebar (260px) in Dark Navy, while the main content area utilizes a 12-column grid with 24px gutters.

Cards are the primary container unit, featuring 24px of internal padding to ensure data does not feel cramped. Layout gaps between cards are strictly maintained at 16px to create a cohesive but distinct modular look. 

**Mobile Adaptation:**
- The sidebar is replaced by a bottom tab bar containing Home, Score, Portfolio, Alerts, and Settings.
- Screen margins reduce to 16px.
- Multi-column card layouts reflow into a single-column stack.

## Elevation & Depth
This design system utilizes a **Tonal Layering** approach combined with **Ambient Shadows** to define hierarchy. 

The base canvas sits at the lowest level in Light Grey. White cards are elevated using a crisp, low-diffusion shadow (`0 1px 3px rgba(0,0,0,0.1)`) which suggests the card is resting just above the surface. This "Flat Plus" approach avoids heavy gradients, relying instead on 1px borders in `#E5E7EB` to provide definition in high-brightness environments. Interactive elements like primary buttons use a slightly deeper shadow on hover to indicate tactility.

## Shapes
The shape language is consistently **Rounded**. A 12px (0.75rem) corner radius is applied to all primary cards and large containers to soften the technical nature of the data. Smaller components like input fields and buttons utilize an 8px (0.5rem) radius. Status chips and badges use a fully rounded (pill) shape to distinguish them from actionable buttons and structural containers.

## Components

### Buttons
Primary buttons are solid LendIQ Red with white text. Secondary buttons use a transparent background with a Dark Navy border and text. All buttons feature medium weight typography and 8px rounded corners.

### Cards
Cards are the core of the experience. They must have a white background, 12px rounded corners, a 1px border (`#E5E7EB`), and the standard ambient shadow. Internal padding is strictly 24px.

### Inputs & Selects
Input fields use a 1px border with a 4px focus ring in a semi-transparent LendIQ Red. Labels are placed above the field using the `label-md` typography style.

### Chips & Badges
Used for status (e.g., "Approved", "Pending"). These use a "Soft Tonal" style—lightly tinted backgrounds with darker text (e.g., Success Green background at 10% opacity with solid Success Green text).

### Metrics Displays
Large numerical displays should be paired with a small trend indicator (arrow icon + percentage) to provide immediate context for lending performance.

### Navigation
- **Sidebar (Desktop):** Dark Navy background with high-contrast white text for active states and 60% opacity for inactive states.
- **Tab Bar (Mobile):** White background with a top border, using 24px line icons and 10px labels.