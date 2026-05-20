import Foundation

enum TransactionType: String, Codable {
    case inflow = "inflow"
    case outflow = "outflow"
    case transfer = "transfer"
    case adjustment = "adjustment"

    var isExpense: Bool {
        self == .outflow
    }

    var prefix: String {
        self == .inflow ? "+" : "-"
    }
}

struct Transaction: Codable, Identifiable {
    let id: UUID
    let userId: UUID
    let accountId: UUID
    let categoryId: UUID?
    let amountCents: Int
    let balanceAfterCents: Int
    let date: Date
    let description: String
    let transactionType: String
    let payee: String?
    let notes: String?
    let isReconciled: Bool
    let createdAt: Date

    var category: String?
    var typeEnum: TransactionType {
        TransactionType(rawValue: transactionType) ?? .outflow
    }

    var amountDollars: Double {
        Double(amountCents) / 100.0
    }

    var formattedAmount: String {
        let prefix = typeEnum == .inflow ? "+" : "-"
        return "\(prefix)$\(String(format: "%.2f", abs(amountDollars)))"
    }

    enum CodingKeys: String, CodingKey {
        case id, userId = "user_id", accountId = "account_id"
        case categoryId = "category_id"
        case amountCents = "amount_cents"
        case balanceAfterCents = "balance_after_cents"
        case date, description
        case transactionType = "transaction_type"
        case payee, notes
        case isReconciled = "is_reconciled"
        case createdAt = "created_at"
    }
}

struct CreateTransactionRequest: Codable {
    let accountId: UUID
    let transactionType: String
    let amount: Double
    let date: Date
    let description: String
    let payee: String?
    let categoryId: UUID?
    let notes: String?

    enum CodingKeys: String, CodingKey {
        case accountId = "account_id"
        case transactionType = "transaction_type"
        case amount, date, description, payee
        case categoryId = "category_id"
        case notes
    }
}