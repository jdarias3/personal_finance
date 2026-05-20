import Foundation

struct Category: Codable, Identifiable {
    let id: UUID
    let userId: UUID
    let name: String
    let icon: String?
    let color: String?
    let parentId: UUID?
    let createdAt: Date
}

struct CreateCategoryRequest: Codable {
    let name: String
    let icon: String?
    let color: String?
}