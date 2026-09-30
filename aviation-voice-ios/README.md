# Avionics VoiceOps

**Swift · iOS · Xcode · iPhone · Voice Commands · Aviation Data**

Avionics VoiceOps is a portfolio iOS prototype that demonstrates how structured aviation data can be exposed through a simple, read-only voice interface.

The project uses a **vendor-neutral synthetic avionics data model**. It does **not** contain proprietary Collins Aerospace / Rockwell Collins data, SDKs, credentials, interface specifications, or confidential source material.

## What it does

The app can load a synthetic flight snapshot and answer read-only voice queries such as:

- “What is our altitude?”
- “What is the groundspeed?”
- “What is the current heading?”
- “What is the next waypoint?”
- “How much fuel remains?”
- “What is the destination weather status?”
- “What is our ETA?”
- “Read the flight status.”

The prototype never sends commands to an aircraft, FMS, radio, autopilot, navigation system, or other safety-critical system.

## Technology

- Swift
- SwiftUI
- iOS
- Xcode
- Apple Speech framework
- AVFAudio
- JSON / Codable
- MVVM-style separation of concerns
- XCTest
- XcodeGen-compatible project specification

## Architecture

```text
Synthetic flight JSON
        ↓
MockAvionicsService
        ↓
FlightSnapshot
        ↓
VoiceCommandInterpreter ← SpeechRecognizer
        ↓
SwiftUI
```

The data-service boundary is intentional. An approved vendor API or SDK could later replace the mock service without requiring the UI or intent model to be rewritten.

## Repository layout

```text
aviation-voice-ios/
├── README.md
├── project.yml
├── App/
│   ├── AvionicsVoiceOpsApp.swift
│   ├── ContentView.swift
│   └── Info.plist
├── Models/
│   └── FlightSnapshot.swift
├── Services/
│   ├── MockAvionicsService.swift
│   └── SpeechRecognizer.swift
├── Voice/
│   └── VoiceCommandInterpreter.swift
├── Resources/
│   └── flight_snapshot.json
├── Tests/
│   └── VoiceCommandInterpreterTests.swift
└── docs/
    ├── ARCHITECTURE.md
    ├── BUILD.md
    ├── DATA_MODEL.md
    ├── PRIVACY.md
    ├── SAFETY_AND_LIMITATIONS.md
    └── VOICE_COMMANDS.md
```

## Apple privacy behavior

The project declares:

- `NSMicrophoneUsageDescription`
- `NSSpeechRecognitionUsageDescription`

Permissions are requested when the user chooses to enable voice input, rather than automatically on app launch.

See [docs/PRIVACY.md](docs/PRIVACY.md).

## Collins / Rockwell Collins note

Collins Aerospace and Rockwell Collins are third-party trademarks. This repository does not claim affiliation, endorsement, certification, or access to proprietary vendor systems.

If authorized vendor data or an approved SDK becomes available later, it should be integrated behind the `AvionicsDataProviding` protocol rather than copied directly into UI code.

## Recommended GitHub topics

If this project is later split into its own repository, recommended topics are:

`swift` · `ios` · `xcode` · `iphone` · `swiftui` · `voice-commands` · `speech-recognition` · `aviation` · `avionics` · `json`

## Portfolio boundaries

This is an educational software portfolio artifact. It is not certified avionics software and must not be used for navigation, dispatch, maintenance release, operational flight planning, or flight-critical decision-making.
