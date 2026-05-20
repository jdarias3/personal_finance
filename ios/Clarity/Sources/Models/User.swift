import Foundation

struct User: Codable, Identifiable {
    let id: UUID
    let email: String
    let fullName: String?
    let isActive: Bool
    let createdAt: Date
}

struct LoginRequest: Codable {
    let email: String
    let password: String
}

struct LoginResponse: Codable {
    let accessToken: String
    let tokenType: String

    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
        case tokenType = "token_type"
    }
}

struct RegisterRequest: Codable {
    let name: String
    let email: String
    let password: String
}