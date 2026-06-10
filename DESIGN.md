# Design System - SpecTwin

## Product Context
- **What this is:** SpecTwin is a Windows-first scientific desktop application for X-ray emission spectroscopy workflows. It combines digital twin spectrometer simulation, AutoFDMNES material simulation, data processing, visualization, calibration, merging, and event analysis.
- **Who it's for:** Researchers, beamline scientists, materials scientists, and spectroscopy users who need to configure simulations, inspect spectra, align data, and move between experimental and simulated results.
- **Space/industry:** Scientific instrumentation, spectroscopy, materials research, and lab data analysis.
- **Project type:** Data-dense desktop workstation built with Dear PyGui, not a marketing site or consumer app.
- **Memorable thing:** This should feel like serious spectrometer software: calm, precise, instrument-grade, and trustworthy under long research sessions.

## Aesthetic Direction
- **Direction:** Industrial/Utilitarian.
- **Decoration level:** Minimal to intentional. Decoration should come from measured grid lines, plot structure, spectroscopy accents, and disciplined spacing rather than ornamental UI.
- **Mood:** Dense but calm. The application should feel like an analysis console that helps users trust numbers, not a generic dark dashboard or a white corporate launcher.
- **Current design problem:** The start screen uses a white logo-centric layout, while the main application mostly inherits default Dear PyGui styling. Individual modules define local colors and spacing, so the product currently lacks one visual language.

## Design Principles
- **Data first:** Plots, spectra, tables, and selected parameters are the primary content. Chrome should frame the work, not compete with it.
- **Workflow visible:** Each module should expose where the user is in the process: choose data, configure, run, inspect, export.
- **Status must be semantic:** Idle, running, success, warning, error, selected, and excluded states need consistent colors across every module.
- **No generic SaaS patterns:** Avoid oversized hero areas, colorful icon cards, bubbly buttons, purple gradients, and marketing-style layouts.
- **Desktop density:** Use compact, scannable panels. Users will repeat tasks and compare numbers, so wasted space hurts the work.

## Typography
- **Display/Hero:** Source Sans 3 Semibold - clean, serious, readable, and less generic than the usual web-app defaults.
- **Body:** Source Sans 3 Regular - strong for labels, paragraphs, controls, and mixed scientific text.
- **UI/Labels:** Source Sans 3 Semibold for section headers and labels.
- **Data/Tables:** IBM Plex Mono - use for energies, pixel positions, HKL values, seeds, IDs, and tabular numeric output. Enable tabular numbers where supported.
- **Code/Paths:** IBM Plex Mono.
- **Dear PyGui loading strategy:** Keep the existing local Verdana font as a fallback while introducing a project font loader that can register Source Sans 3 and IBM Plex Mono from local files. Do not depend on runtime network font loading in the desktop app.
- **Scale:** 12 px micro labels, 14 px dense table/body, 16 px default UI, 18 px section title, 22 px module title, 28 px start screen title.

## Color
- **Approach:** Restrained, with a scientific accent palette. Neutrals carry the interface; color appears only for state, selection, and plotted meaning.
- **Primary:** `#1FB6D5` spectral cyan - primary action, active tab, selected workflow state, important plot overlays.
- **Secondary:** `#F2A93B` warm amber - warnings, peak-picking highlights, "attention needed" states, active measurement annotations.
- **Background:** `#101417` graphite black - main desktop background.
- **Surface 1:** `#171D21` primary panel background.
- **Surface 2:** `#20282D` raised panel, tabs, modal surface.
- **Surface 3:** `#2B353B` input and table header surface.
- **Border:** `#3A464D` normal border and plot frame.
- **Border strong:** `#56636B` focused field or active panel border.
- **Text primary:** `#EEF5F7`.
- **Text secondary:** `#AAB7BE`.
- **Text muted:** `#74828A`.
- **Success:** `#39B980`.
- **Warning:** `#F2A93B`.
- **Error:** `#E15D5D`.
- **Info:** `#63A7F2`.
- **Excluded state:** `#B85C5C`, never pure red unless destructive.
- **Included state:** `#39B980`, paired with a label or check state, not color alone.
- **Plot colors:** cyan `#1FB6D5`, amber `#F2A93B`, green `#39B980`, blue `#63A7F2`, rose `#D96C9F`, violet `#8F7EF5`. Use consistently by series role, not randomly.
- **Light mode:** Not required for the main workstation. If added, redesign surfaces instead of simply inverting colors.

## Spacing
- **Base unit:** 4 px.
- **Density:** Compact for desktop controls, comfortable inside major plot and table areas.
- **Scale:** 2xs 2 px, xs 4 px, sm 8 px, md 16 px, lg 24 px, xl 32 px, 2xl 48 px, 3xl 64 px.
- **Panel padding:** 12 px compact panels, 16 px primary work panels.
- **Control gaps:** 8 px between related controls, 16 px between control groups, 24 px between workflow sections.
- **Plot gutters:** Minimum 16 px around plots so axis labels do not visually crash into controls.

## Layout
- **Approach:** Grid-disciplined workstation.
- **Application shell:** Persistent left module rail, top context/header strip, main content work area.
- **Left rail:** 240 px target width. Module labels should be short and consistent: Digital Twin, AutoFDMNES, Data Processing, Merge Data, Visualization, Event Analysis.
- **Main content:** Use a 12-column mental grid at 1920 px. For Dear PyGui, implement as predictable child-window widths and groups.
- **Module pages:** Start with a compact title/status row, then tabs or workflow steps, then split panes for controls and plots.
- **Digital Twin:** Keep Lines, Simulation, Optimization, Results, but make each tab use the same left-control/right-output structure.
- **AutoFDMNES:** Treat Materials, Edges/CIF, Parameters, Run/Peaks as a visible workflow. The user should see progression, not only tabs.
- **Data modules:** Use left setup panel, center plot/table canvas, bottom or right status/export panel.
- **Border radius:** Small and utilitarian. 2 px for inputs, 4 px for buttons and panels, 6 px for modals. Avoid large rounded cards.
- **Max content width:** No artificial max width in the desktop app. Use available screen real estate for plots and tables.

## Components
- **Buttons:** Primary actions use spectral cyan fill. Secondary actions use surface fill with border. Destructive actions use error border/fill only when needed.
- **Tabs:** Active tab uses cyan top or bottom accent, not large filled color blocks.
- **Tables:** Sticky-looking headers, monospace numeric cells, alternating row shade at low contrast, selected row with cyan outline or left marker.
- **Inputs:** Dark field, clear label, 2 px focus ring in cyan. Numeric scientific inputs should align labels and values.
- **Status text:** Replace scattered print-style messages with a consistent status strip pattern: icon/label, message, timestamp or run state where useful.
- **Modals:** Use for blocking choices only. Keep modal titles specific and action buttons aligned consistently.
- **Plots:** Plot backgrounds should match Surface 1 or slightly darker, with subtle grid lines. Peak markers should use amber, selected peaks cyan, errors red.
- **Periodic table:** Included and excluded states must use green/red plus text, tooltip, or selection summary. Do not rely on color alone.

## Motion
- **Approach:** Minimal-functional.
- **Duration:** Micro 50-100 ms, short 150-250 ms, medium 250-400 ms.
- **Use motion for:** Tab changes, loading/running indicators, status updates, and modal appearance.
- **Avoid motion for:** Plot redraws, numeric table updates, or anything that could distract during analysis.

## Safe Choices
- **Dark workstation base:** Scientific users spend time comparing data and plots; dark graphite reduces visual fatigue and supports plot contrast.
- **Left rail plus tabbed work area:** This matches desktop analysis tools and keeps repeated workflows fast.
- **Semantic status colors:** Users need to know what is selected, running, failed, and ready without re-learning each module.

## Creative Risks
- **Spectral cyan as the primary identity color:** Many scientific tools default to blue-gray or plain white. Cyan gives SpecTwin a recognizable instrument-console face without becoming decorative.
- **Amber peak-picking language:** Using amber for selected peaks, warnings, and measurement attention gives spectral interactions a memorable visual grammar.
- **Workflow step framing for AutoFDMNES:** Tabs alone hide process. A stepper-style treatment makes the simulation journey feel intentional and reduces user uncertainty.

## Implementation Guidance
- Add a shared Dear PyGui theme module, for example `Source/UI/theme.py`, and make `StartScreen.py`, `SpectwinMain.py`, and module UIs consume it.
- Centralize colors as named tokens. Do not hard-code `(0, 200, 0)`, `(255, 165, 0)`, or `(150, 150, 150)` inside modules.
- Centralize font registration. Use Source Sans 3 and IBM Plex Mono if local font files are added; keep Verdana as fallback until then.
- Create helper functions for section headers, status strips, primary buttons, secondary buttons, warning text, and data tables.
- Replace manual spacer-based centering on the start screen with a real grid/group layout.
- Review every module for text hierarchy. Section headings, helper text, labels, and output values should not all share the same visual weight.
- Keep screenshots and QA notes after each major visual pass. This product needs visual consistency across modules, not one polished entry screen.

## Decisions Log
| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-06-08 | Initial design system created | Created by design consultation from README and Dear PyGui source inspection. |
| 2026-06-08 | Industrial/Utilitarian direction | Fits a spectroscopy desktop workstation better than marketing, playful, or generic dashboard aesthetics. |
| 2026-06-08 | Graphite dark theme with cyan/amber accents | Supports plot contrast and gives selected peaks, workflow state, and status messages consistent meaning. |
