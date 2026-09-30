import Foundation

struct FlightSnapshot: Codable, Equatable {
    let flightNumber: String
    let aircraftType: String
    let origin: String
    let destination: String
    let altitudeFeet: Int
    let groundSpeedKnots: Int
    let headingDegrees: Int
    let nextWaypoint: String
    let distanceToDestinationNM: Int
    let fuelRemainingLbs: Int
    let estimatedArrivalLocal: String
    let destinationWeatherStatus: String
}
