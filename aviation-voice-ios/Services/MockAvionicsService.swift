import Foundation

protocol AvionicsDataProviding {
    func loadSnapshot() throws -> FlightSnapshot
}

enum AvionicsDataError: Error {
    case resourceNotFound
    case decodingFailed
}

final class MockAvionicsService: AvionicsDataProviding {
    func loadSnapshot() throws -> FlightSnapshot {
        guard let url = Bundle.main.url(
            forResource: "flight_snapshot",
            withExtension: "json"
        ) else {
            throw AvionicsDataError.resourceNotFound
        }

        do {
            let data = try Data(contentsOf: url)
            return try JSONDecoder().decode(FlightSnapshot.self, from: data)
        } catch {
            throw AvionicsDataError.decodingFailed
        }
    }
}
