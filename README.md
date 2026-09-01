<div align="center">

<img src="docs/img/logo.png" width="110" alt="Amethyst logo">

# Amethyst

**Your colors and your resolution, per game, switched for you.**

Amethyst is a Windows app that sets digital vibrance, brightness, contrast, gamma and
resolution the way the NVIDIA control panel does, but per game. Build a profile for
Valorant, another one for CS2, and the moment the game starts your screen switches over.
When you close it, everything goes back.

[![Download](https://img.shields.io/github/v/release/ImKirit/Amethyst?color=A855F7&label=download&sort=semver)](https://github.com/ImKirit/Amethyst/releases/latest)
[![License](https://img.shields.io/badge/license-MIT-181029)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-181029)](#install)

<img src="docs/img/main-display.png" width="820" alt="Amethyst, display page with color sliders">

</div>

---

## Why?

Every competitive player ends up with the same ritual: open the NVIDIA panel before a match,
push digital vibrance up, switch to a stretched resolution, and then undo all of it afterwards
because the desktop looks radioactive. Doing that by hand, twice per session, gets old fast.

So Amethyst binds those settings to the game's process instead of to your memory. One profile
per game, applied when the executable shows up, reverted when it disappears. Two decisions make
it safe to leave running: the state from before the first change is written to disk, so even a
crash cannot leave your screen tinted, and resolution changes are applied temporarily, so they
never survive a reboot.

## Getting started

1. **Install and launch Amethyst.** No setup wizard, no account. The Display page shows what
   your machine actually supports before you change anything.

2. **Create a profile.** Click **New profile** and pick a template. Fifteen games are
   preconfigured with their process names and a sane starting point.

   <img src="docs/img/tour-templates.png" width="330" alt="Template menu with preconfigured games">

3. **Check the trigger.** Templates already carry the right executable. For anything else,
   start the game, then use **From running programs** and pick it from the list.

   <img src="docs/img/tour-picker.png" width="430" alt="Picker showing running programs">

4. **Dial in the look.** Vibrance, brightness, contrast, gamma and the color balance sit in one
   panel, resolution in the next. The swatch strip above the sliders previews the result, and
   **Preview for 10 seconds** puts it on the real screen and takes it back off.

   <img src="docs/img/main-profiles.png" width="620" alt="Profile editor with color and resolution">

5. **Start the game.** Amethyst switches within a second or two, the profile is marked
   **active**, and closing the game restores your desktop values.

   <img src="docs/img/main-active.png" width="620" alt="Profiles page while a game is running">

## Features

### Tune

- **Digital vibrance.** Straight through NVAPI on the same 0 to 100 scale the NVIDIA panel
  uses, where 50 is normal Windows saturation. It lives in the driver scanout, so it applies
  in full-screen games as well.
- **Brightness, contrast, gamma.** Ranges match the NVIDIA panel: brightness -50 to +50,
  contrast 0 to 100, gamma 0.30 to 2.80.
- **Color balance.** Separate red, green and blue gain from 50 to 150 percent, for a warmer or
  cooler picture without touching the monitor menu.
- **Resolution and refresh rate.** Every mode the driver reports, including custom ones you
  created in the NVIDIA panel. Anything that is not the native aspect ratio is labelled
  **stretched** so you can find 1440x1080 at a glance.
- **Per display.** Every profile targets one monitor, picked by name.

### Automate

- **Process triggers.** A profile lists the executables that activate it, for example
  `VALORANT-Win64-Shipping.exe`. Several names per profile are fine.
- **The resolution stays put.** Games change the display mode themselves when they go full
  screen, and Windows restores the desktop mode on alt tab. Amethyst checks every 0.7 seconds
  and puts your profile resolution back, so a stretched profile does not quietly fall back to
  native halfway through a match.
- **Automatic switch back.** Close the game and your desktop values return. Turn that off per
  profile when you want the look to stick around.
- **Fifteen templates.** Valorant, CS2, Fortnite, Apex, Siege, Overwatch 2, Call of Duty,
  Rocket League, League of Legends, Minecraft, PUBG, Rust, Tarkov, Dota 2 and GTA V.
- **Clear priority.** When two profiles match at once, the upper one in the list wins. Move
  profiles with the arrow buttons.
- **Tray and autostart.** Closing the window keeps Amethyst in the tray, where the menu applies
  any profile by hand or resets everything. One switch starts it with Windows.

### Stay in control

- **Nothing is left behind.** The gamma ramp, the vibrance level and the display mode from
  before the first change are captured and written to `baseline.json`. If Amethyst is killed,
  the next start restores them.
- **Resolution changes are temporary.** They are applied without writing to the registry, so a
  reboot lands you back on your normal desktop.
- **Honest diagnostics.** The Display page names what works on your machine and why something
  does not, instead of silently doing nothing.
- **A second path for brightness.** When the gamma ramp is blocked, Amethyst can drive your
  monitor over DDC/CI instead.
- **A badge that tells you what is applied.** Optional, draggable, always on top: it says
  whether you are on a stretched or a native mode right now. Exclusive full screen paints over
  it, so it shows on the desktop and in borderless windowed mode.
- **Updates itself.** Amethyst checks the releases of this repository on start and can replace
  its own exe with one click.
- **The wheel does not touch your settings.** Scrolling over a slider or a dropdown scrolls the
  page, it never changes the value by accident.

## Screens

| | |
|---|---|
| **Display.** Desktop color and resolution, plus what your machine supports. | **Profiles.** List on the left, full editor on the right. |
| <img src="docs/img/main-display.png" width="420" alt="Display page"> | <img src="docs/img/main-profiles.png" width="420" alt="Profiles page"> |
| **While gaming.** The active profile is marked and shown in the title bar. | **Settings.** Behaviour, brightness path, badge, updates, diagnostics. |
| <img src="docs/img/main-active.png" width="420" alt="Active profile"> | <img src="docs/img/main-settings.png" width="420" alt="Settings page"> |

The optional badge, draggable anywhere on your screen:

<img src="docs/img/tour-badge.png" width="260" alt="Resolution badge showing a stretched mode">

## What works on your machine

Not every part of the color pipeline is available everywhere, and Amethyst tells you which one
you have instead of failing quietly.

| Setting | Needs | Notes |
|---|---|---|
| Digital vibrance | NVIDIA GPU with driver | Works even when the gamma ramp is blocked |
| Brightness, contrast, gamma, color balance | GDI gamma ramp | Blocked by HDR, by automatic color management and by kernel anti-cheats |
| Brightness and contrast, fallback | Monitor with DDC/CI enabled | Slower, and many monitors ship with DDC/CI off |
| Resolution and refresh rate | Any GPU | Always available |

**If the color sliders are greyed out**, the Display page names the cause. The common ones:

- **A kernel anti-cheat is running.** Riot Vanguard blocks the gamma ramp system wide, for
  every program, from boot. Digital vibrance and resolution keep working, which is exactly the
  combination that matters for Valorant.
- **HDR or automatic color management is on** for that monitor. Turn it off in Windows under
  Settings, System, Display, and the sliders come back.
- **The range feels clamped.** Windows limits how far the ramp may deviate until
  `GdiIcmGammaRange` is set. Settings has a button for it; it needs administrator rights and
  applies after the next sign-in.

## Stretched resolutions

Amethyst switches the resolution. Whether the picture is then stretched or shown with black
bars is decided by the graphics driver, so set that once:

1. Open the NVIDIA control panel, **Adjust desktop size and position**.
2. Scaling mode **Full-screen**, and **Perform scaling on: GPU**.
3. Tick **Override the scaling mode set by games and programs**.

Resolutions that are not the native aspect ratio, such as 1440x1080 or 1280x960, are labelled
**stretched** in the dropdown. Custom resolutions you created in the NVIDIA panel show up in
that list automatically.

Games take the display mode into their own hands: alt tab out of a full screen game, or switch
between windowed and full screen, and the mode goes back to native. Amethyst notices that
within a second and sets your profile resolution again. If you ever want the game to have the
last word, turn off **Hold the resolution while a game runs** in the settings.

## How data is stored

```
%LOCALAPPDATA%\Amethyst\
├── profiles.json     your game profiles, in order of priority
├── settings.json     behaviour plus the desktop profile
├── baseline.json     state from before the first change, deleted on a clean exit
└── amethyst.log      what was applied and what was refused
```

Plain JSON, no database, no registry keys beyond the optional autostart entry. Delete the
folder and Amethyst starts fresh.

## Install

**Windows 10 or 11.** An NVIDIA card is needed for digital vibrance; everything else works on
any GPU.

### 1. Download the release

Grab `Amethyst.exe` from the [latest release](https://github.com/ImKirit/Amethyst/releases/latest)
and run it. One file, no installer, nothing to set up. It updates itself from then on.

Windows SmartScreen warns about it because the file is not code signed. Choose "More info",
then "Run anyway". Every release lists the SHA256 of the exe if you want to check it first:

```bash
certutil -hashfile Amethyst.exe SHA256
```

### 2. Build it yourself

```bash
git clone https://github.com/ImKirit/Amethyst.git
cd Amethyst
pip install -r requirements.txt
python tools/build.py
```

The result is `dist/Amethyst.exe`, the same single file, with no dependencies on the target
machine. `python tools/build.py --folder` builds an unpacked folder instead, which starts
noticeably faster.

### Updates

Amethyst asks the GitHub API for the latest release on start, compares it against its own
version and offers the update. Installing means: the new exe is downloaded, the running one is
renamed to `.old`, the new one takes its place and Amethyst restarts. The leftover `.old` file
is removed on the next start. Turn the check off under Settings, Updates.

## Development

```bash
pip install -r requirements.txt     # PySide6, the only dependency
python -m amethyst                  # run from source, with console output
pythonw run.pyw                     # run without a console window
python tools/screenshots.py         # regenerate the images in docs/img
python tools/build.py               # package as dist/Amethyst.exe
```

The Windows side is plain `ctypes`, no compiled extension: `amethyst/winapi/` holds one module
per capability (`gamma`, `nvapi`, `displays`, `ddcci`, `processes`, `autostart`), and each one
reports whether it actually works instead of raising. `engine.py` owns the state machine that
decides which profile is active, captures the baseline and restores it. Everything under
`amethyst/ui/` is PySide6 with a single stylesheet in `ui/theme.py`, so the whole look changes
from one file.

## License

[MIT](LICENSE) © ImKirit
