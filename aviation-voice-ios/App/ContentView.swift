import SwiftUI

struct ContentView: View {
    @StateObject private var speech = SpeechRecognizer()

    @State private var snapshot: FlightSnapshot?
    @State private var response = "Load the synthetic flight snapshot, then use Push to Talk."
    @State private var errorMessage = ""

    private let service: AvionicsDataProviding = MockAvionicsService()
    private let interpreter = VoiceCommandInterpreter()

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    header

                    if let snapshot {
                        snapshotPanel(snapshot)
                    }

                    voicePanel
                    responsePanel
                    notices
                }
                .padding()
            }
            .navigationTitle("VoiceOps")
            .task {
                loadSnapshot()
            }
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("Avionics VoiceOps")
                .font(.largeTitle.bold())

            Text("Read-only aviation data prototype")
                .foregroundStyle(.secondary)
        }
    }

    private func snapshotPanel(_ snapshot: FlightSnapshot) -> some View {
        GroupBox("Flight Snapshot") {
            VStack(alignment: .leading, spacing: 8) {
                row("Flight", snapshot.flightNumber)
                row("Route", "\(snapshot.origin) → \(snapshot.destination)")
                row("Aircraft", snapshot.aircraftType)
                row("Altitude", "\(snapshot.altitudeFeet.formatted()) ft")
                row("Groundspeed", "\(snapshot.groundSpeedKnots) kt")
                row("Heading", "\(snapshot.headingDegrees)°")
                row("Next waypoint", snapshot.nextWaypoint)
                row("Fuel remaining", "\(snapshot.fuelRemainingLbs.formatted()) lb")
            }
        }
    }

    private var voicePanel: some View {
        GroupBox("Voice Command") {
            VStack(alignment: .leading, spacing: 12) {
                Text(
                    speech.transcript.isEmpty
                    ? "No command recognized yet."
                    : speech.transcript
                )
                .frame(maxWidth: .infinity, alignment: .leading)

                HStack {
                    Button(
                        speech.isListening ? "Stop Listening" : "Push to Talk"
                    ) {
                        if speech.isListening {
                            speech.stopListening()
                        } else {
                            Task {
                                await speech.startListening()
                            }
                        }
                    }
                    .buttonStyle(.borderedProminent)

                    Button("Run Command") {
                        runRecognizedCommand()
                    }
                    .buttonStyle(.bordered)
                    .disabled(speech.transcript.isEmpty)
                }
            }
        }
    }

    private var responsePanel: some View {
        GroupBox("Response") {
            Text(response)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    @ViewBuilder
    private var notices: some View {
        if !speech.statusMessage.isEmpty {
            Text(speech.statusMessage)
                .font(.footnote)
                .foregroundStyle(.orange)
        }

        if !errorMessage.isEmpty {
            Text(errorMessage)
                .font(.footnote)
                .foregroundStyle(.red)
        }

        Text("Portfolio prototype only — not for operational or flight-critical use.")
            .font(.footnote)
            .foregroundStyle(.secondary)
    }

    private func loadSnapshot() {
        do {
            snapshot = try service.loadSnapshot()
        } catch {
            errorMessage = "The synthetic flight snapshot could not be loaded."
        }
    }

    private func runRecognizedCommand() {
        guard let snapshot else {
            return
        }

        let intent = interpreter.intent(for: speech.transcript)
        response = interpreter.response(
            for: intent,
            snapshot: snapshot
        )
    }

    private func row(
        _ label: String,
        _ value: String
    ) -> some View {
        HStack {
            Text(label)
                .foregroundStyle(.secondary)

            Spacer()

            Text(value)
                .fontWeight(.semibold)
        }
    }
}
