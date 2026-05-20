import Foundation

enum AccountType: String, Codable, CaseIterable {
    case checking = "checking"
    case savings = "savings"
    case credit = "credit"
    case loan = "loan"
    case cash = "cash"
    case investment = "investment"

    var displayName: String {
        switch self {
        case .checking: return "Checking"
        case .savings: return "Savings"
        case .credit: return "Credit Card"
        case .loan: return "Loan"
        case .cash: return "Cash"
        case .investment: return "Investment"
        }
    }

    var icon: String {
        switch self {
        case .checking: return "building.columns"
        case .savings: return "banknote"
        case .credit: return "creditcard"
        case .loan: return "house"
        case .cash: return "dollarsign.circle"
        case .investment: return "chart.line.uptrend.xyaxis"
        }
    }
}

struct Account: Codable, Identifiable {
    let id: UUID
    let userId: UUID
    let name: String
    let accountType: String
    let institution: String?
    let isActive: Bool
    let createdAt: Date
    let updatedAt: Date

    var balance: Int = 0

    var typeEnum: AccountType {
        AccountType(rawValue: accountType) ?? .checking
    }

    enum CodingKeys: String, CodingKey {
        case id, userId = "user_id", name
        case accountType = "account_type"
        case institution
        case isActive = "is_active"
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }
}

struct CreateAccountRequest: Codable {
    let name: String
    let accountType: String
    let institution: String?

    enum CodingKeys: String, CodingKey {
        case name
        case accountType = "account_type"
        case institution
    }
}