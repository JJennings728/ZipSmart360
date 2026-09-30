import AVFAudio
import Foundation
import Speech

@MainActor
final class SpeechRecognizer: ObservableObject {
    @Published private(set) var transcript = ""
    @Published private(set) var isListening = false
    @Published private(set) var statusMessage = ""

    private let recognizer = SFSpeechRecognizer(locale: Locale(identifier: "en-US"))
    private let audioEngine = AVAudioEngine()

    private var request: SFSpeechAudioBufferRecognitionRequest?
    private var task: SFSpeechRecognitionTask?

    func ensureAuthorization() async -> Bool {
        let speechStatus = await requestSpeechAuthorization()

        guard speechStatus == .authorized else {
            statusMessage = speechAuthorizationMessage(for: speechStatus)
            return false
        }

        let microphoneGranted = await requestMicrophoneAuthorization()

        guard microphoneGranted else {
            statusMessage = "Microphone access is required for push-to-talk voice commands."
            return false
        }

        statusMessage = ""
        return true
    }

    func startListening() async {
        guard await ensureAuthorization() else {
            return
        }

        guard let recognizer, recognizer.isAvailable else {
            statusMessage = "Speech recognition is currently unavailable."
            return
        }

        stopListening()

        do {
            try configureAudioSession()

            let inputNode = audioEngine.inputNode
            let recognitionRequest = SFSpeechAudioBufferRecognitionRequest()

            recognitionRequest.shouldReportPartialResults = true
            request = recognitionRequest
            transcript = ""

            let format = inputNode.outputFormat(forBus: 0)

            inputNode.installTap(
                onBus: 0,
                bufferSize: 1024,
                format: format
            ) { buffer, _ in
                recognitionRequest.append(buffer)
            }

            audioEngine.prepare()
            try audioEngine.start()
            isListening = true

            task = recognizer.recognitionTask(
                with: recognitionRequest
            ) { [weak self] result, error in
                guard let self else {
                    return
                }

                if let result {
                    Task { @MainActor in
                        self.transcript = result.bestTranscription.formattedString

                        if result.isFinal {
                            self.stopListening()
                        }
                    }
                }

                if error != nil {
                    Task { @MainActor in
                        self.stopListening()
                    }
                }
            }
        } catch {
            statusMessage = "Unable to start voice recognition."
            stopListening()
        }
    }

    func stopListening() {
        if audioEngine.isRunning {
            audioEngine.stop()
        }

        audioEngine.inputNode.removeTap(onBus: 0)
        request?.endAudio()
        task?.cancel()

        request = nil
        task = nil
        isListening = false

        try? AVAudioSession.sharedInstance().setActive(
            false,
            options: .notifyOthersOnDeactivation
        )
    }

    private func configureAudioSession() throws {
        let session = AVAudioSession.sharedInstance()

        try session.setCategory(
            .record,
            mode: .measurement,
            options: [.duckOthers]
        )

        try session.setActive(
            true,
            options: .notifyOthersOnDeactivation
        )
    }

    private func requestSpeechAuthorization() async -> SFSpeechRecognizerAuthorizationStatus {
        if SFSpeechRecognizer.authorizationStatus() != .notDetermined {
            return SFSpeechRecognizer.authorizationStatus()
        }

        return await withCheckedContinuation { continuation in
            SFSpeechRecognizer.requestAuthorization { status in
                continuation.resume(returning: status)
            }
        }
    }

    private func requestMicrophoneAuthorization() async -> Bool {
        switch AVAudioApplication.shared.recordPermission {
        case .granted:
            return true

        case .denied:
            return false

        case .undetermined:
            return await withCheckedContinuation { continuation in
                AVAudioApplication.requestRecordPermission { granted in
                    continuation.resume(returning: granted)
                }
            }

        @unknown default:
            return false
        }
    }

    private func speechAuthorizationMessage(
        for status: SFSpeechRecognizerAuthorizationStatus
    ) -> String {
        switch status {
        case .authorized:
            return ""

        case .denied:
            return "Speech recognition permission was denied."

        case .restricted:
            return "Speech recognition is restricted on this device."

        case .notDetermined:
            return "Speech recognition permission has not been determined."

        @unknown default:
            return "Speech recognition is unavailable."
        }
    }
}
