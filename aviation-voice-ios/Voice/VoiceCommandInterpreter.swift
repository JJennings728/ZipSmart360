import Foundation

enum VoiceIntent: Equatable {
    case altitude
    case groundSpeed
    case heading
    case nextWaypoint
    case fuelRemaining
    case destinationWeather
    case arrivalTime
    case flightStatus
    case unknown
}

struct VoiceCommandInterpreter {
    func intent(for transcript: String) -> VoiceIntent {
        let command = transcript
            .lowercased()
            .trimmingCharacters(in: .whitespacesAndNewlines)

        if command.contains("altitude") {
            return .altitude
        }

        if command.contains("groundspeed")
            || command.contains("ground speed")
            || command.contains("speed") {
            return .groundSpeed
        }

        if command.contains("heading") {
            return .heading
        }

        if command.contains("next waypoint")
            || command.contains("waypoint") {
            return .nextWaypoint
        }

        if command.contains("fuel") {
            return .fuelRemaining
        }

        if command.contains("weather") {
            return .destinationWeather
        }

        if command.contains("arrival")
            || command.contains("eta") {
            return .arrivalTime
        }

        if command.contains("flight status")
            || command == "status"
            || command.contains("read the flight status") {
            return .flightStatus
        }

        return .unknown
    }

    func response(
        for intent: VoiceIntent,
        snapshot: FlightSnapshot
    ) -> String {
        switch intent {
        case .altitude:
            return "Current altitude is \(snapshot.altitudeFeet.formatted()) feet."

        case .groundSpeed:
            return "Current groundspeed is \(snapshot.groundSpeedKnots) knots."

        case .heading:
            return "Current heading is \(snapshot.headingDegrees) degrees."

        case .nextWaypoint:
            return "The next waypoint is \(snapshot.nextWaypoint)."

        case .fuelRemaining:
            return "Fuel remaining is \(snapshot.fuelRemainingLbs.formatted()) pounds."

        case .destinationWeather:
            return "Destination weather status: \(snapshot.destinationWeatherStatus)."

        case .arrivalTime:
            return "Estimated local arrival is \(snapshot.estimatedArrivalLocal)."

        case .flightStatus:
            return "Flight \(snapshot.flightNumber), \(snapshot.origin) to \(snapshot.destination), altitude \(snapshot.altitudeFeet.formatted()) feet, groundspeed \(snapshot.groundSpeedKnots) knots, next waypoint \(snapshot.nextWaypoint)."

        case .unknown:
            return "Command not recognized. Try altitude, groundspeed, heading, waypoint, fuel, weather, arrival, or flight status."
        }
    }
}
