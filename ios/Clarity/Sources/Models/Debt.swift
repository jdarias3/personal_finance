import Foundation

struct Debt: Codable, Identifiable {
    let id: UUID
    let userId: UUID
    let accountId: UUID?
    let name: String
    let initialAmountCents: Int
    let currentBalanceCents: Int
    let interestRate: Int
    let minimumPaymentCents: Int
    let dueDay: Int?
    let createdAt: Date
    let updatedAt: Date

    var currentBalanceDollars: Double { Double(currentBalanceCents) / 100.0 }
    var initialAmountDollars: Double { Double(initialAmountCents) / 100.0 }
    var minimumPaymentDollars: Double { Double(minimumPaymentCents) / 100.0 }
    var interestRatePercent: Double { Double(interestRate) / 100.0 }

    var progressPercent: Double {
        guard initialAmountCents > 0 else { return 0 }
        let paid = initialAmountCents - currentBalanceCents
        return max(0, min(1, Double(paid) / Double(initialAmountCents)))
    }

    var icon: String {
        let lower = name.lowercased()
        if lower.contains("credit") || lower.contains("card") || lower.contains("amex") || lower.contains("visa") || lower.contains("mastercard") { return "creditcard" }
        if lower.contains("mortgage") || lower.contains("house") || lower.contains("home") { return "house" }
        if lower.contains("auto") || lower.contains("car") || lower.contains("vehicle") { return "car" }
        if lower.contains("student") || lower.contains("loan") || lower.contains("heloc") { return "building.columns" }
        if lower.contains("medic") || lower.contains("hospital") { return "cross.case" }
        return "dollarsign.circle"
    }

    var formattedBalance: String {
        String(format: "$%.2f", currentBalanceDollars)
    }

    var formattedMinimumPayment: String {
        String(format: "$%.2f", minimumPaymentDollars)
    }

    var formattedInterestRate: String {
        String(format: "%.2f%%", interestRatePercent)
    }

    enum CodingKeys: String, CodingKey {
        case id
        case userId = "user_id"
        case accountId = "account_id"
        case name
        case initialAmountCents = "initial_amount_cents"
        case currentBalanceCents = "current_balance_cents"
        case interestRate = "interest_rate"
        case minimumPaymentCents = "minimum_payment_cents"
        case dueDay = "due_day"
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }
}

struct DebtSummary: Codable {
    let totalDebtCents: Int
    let totalMinimumPaymentCents: Int
    let weightedAvgRate: Int
    let debtCount: Int

    var totalDebtDollars: Double { Double(totalDebtCents) / 100.0 }
    var totalMinimumPaymentDollars: Double { Double(totalMinimumPaymentCents) / 100.0 }
    var avgInterestRatePercent: Double { Double(weightedAvgRate) / 100.0 }

    enum CodingKeys: String, CodingKey {
        case totalDebtCents = "total_debt_cents"
        case totalMinimumPaymentCents = "total_minimum_payment_cents"
        case weightedAvgRate = "weighted_avg_rate"
        case debtCount = "debt_count"
    }
}

struct PayoffProjection: Codable {
    let debtId: UUID
    let name: String
    let monthsToPayoff: Int
    let totalInterestCents: Int
    let totalCostCents: Int
    let payoffDate: Date
    let monthlySchedule: [ScheduleRow]

    var totalInterestDollars: Double { Double(totalInterestCents) / 100.0 }
    var totalCostDollars: Double { Double(totalCostCents) / 100.0 }

    enum CodingKeys: String, CodingKey {
        case debtId = "debt_id"
        case name
        case monthsToPayoff = "months_to_payoff"
        case totalInterestCents = "total_interest_cents"
        case totalCostCents = "total_cost_cents"
        case payoffDate = "payoff_date"
        case monthlySchedule = "monthly_schedule"
    }
}

struct ScheduleRow: Codable {
    let month: Int
    let paymentCents: Int
    let interestCents: Int
    let principalCents: Int
    let balanceCents: Int

    var paymentDollars: Double { Double(paymentCents) / 100.0 }
    var interestDollars: Double { Double(interestCents) / 100.0 }
    var principalDollars: Double { Double(principalCents) / 100.0 }
    var balanceDollars: Double { Double(balanceCents) / 100.0 }

    enum CodingKeys: String, CodingKey {
        case month
        case paymentCents = "payment_cents"
        case interestCents = "interest_cents"
        case principalCents = "principal_cents"
        case balanceCents = "balance_cents"
    }
}

struct CreateDebtRequest: Codable {
    let name: String
    let initialAmount: Double
    let currentBalance: Double
    let interestRate: Double
    let minimumPayment: Double
    let dueDay: Int?
    let accountId: UUID?

    enum CodingKeys: String, CodingKey {
        case name
        case initialAmount = "initial_amount"
        case currentBalance = "current_balance"
        case interestRate = "interest_rate"
        case minimumPayment = "minimum_payment"
        case dueDay = "due_day"
        case accountId = "account_id"
    }
}