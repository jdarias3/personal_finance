import Foundation

struct DashboardData: Codable {
    let accounts: [AccountWithBalance]
    let netWorth: Int
    let safeToSpend: Int
    let monthlyInflow: Int
    let monthlyOutflow: Int
    let recentTransactions: [Transaction]
    let upcomingBills: [UpcomingBill]
    let insights: [Insight]
}

struct AccountWithBalance: Codable, Identifiable {
    let id: UUID
    let name: String
    let accountType: String
    let institution: String?
    let balance: Int

    var typeEnum: AccountType {
        AccountType(rawValue: accountType) ?? .checking
    }

    var balanceDollars: Double {
        Double(balance) / 100.0
    }

    var formattedBalance: String {
        let prefix = balance < 0 ? "-" : ""
        return "\(prefix)$\(String(format: "%.2f", abs(balanceDollars)))"
    }
}

struct UpcomingBill: Codable, Identifiable {
    let id: UUID
    let name: String
    let amountCents: Int
    let dueDate: Date

    var amountDollars: Double {
        Double(amountCents) / 100.0
    }
}

struct Insight: Codable {
    let type: String
    let message: String
}