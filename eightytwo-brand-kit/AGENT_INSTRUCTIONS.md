---
name: eightytwo-brand-kit
description: Instructions for integrating the official Eighty-Two Limited animated logo badge into any React application.
---

# Eighty-Two Brand Kit Integration Guide

You are an AI agent tasked with integrating the official **Eighty-Two Limited** animated logo badge into a user's React application.

## Assets Provided in this Kit
1. EightyTwoBadge.tsx - The zero-dependency, self-contained SVG React component.
2. eightytwo-badge.css - The CSS file containing the 5 mandatory keyframe animations.

## Integration Steps

### Step 1: Copy the Component
Copy the EightyTwoBadge.tsx file from this kit into the target project's UI components directory (e.g., src/components/ui/ or components/).

### Step 2: Inject the Animation Keyframes
The badge requires 5 specific CSS @keyframes to function correctly (without them, it will not animate).
You must copy the contents of eightytwo-badge.css into the target project's global CSS file (e.g., src/app/globals.css, src/index.css, or styles/globals.css).

### Step 3: Usage & Implementation
You can now import and use the badge in any React file. It accepts the following props:
- size (number | string): Sets the width/height (default: 200).
- speed (number): Animation speed multiplier (default: 1). Lower is slower, higher is faster.
- isStatic (boolean): If 	rue, disables all animations (default: alse).
- className (string): Additional CSS classes for positioning.

### Strict Brand Guidelines
- **DO NOT** alter the internal SVG paths, stroke colors, or hex codes within EightyTwoBadge.tsx. The atomic orange (#ff6b35) and dark slate navy (#141c2e) must remain pristine.
- **DO NOT** modify the keyframe timings or names in the CSS.
- Ensure the parent container does not clip the SVG overflow: visible property if you are applying glow effects.
