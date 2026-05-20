import Foundation

@MainActor
class DashboardViewModel: ObservableObject {
    @Published var accounts: [AccountWithBalance] = []
    @Published var netWorth: Int = 0
    @Published var safeToSpend: Int = 0
    @Published var monthlyInflow: Int = 0
    @Published var monthlyOutflow: Int = 0
    @Published var recentTransactions: [Transaction] = []
    @Published var upcomingBills: [UpcomingBill] = []
    @Published var insights: [Insight] = []
    @Published var isLoading = false
    @Published var errorMessage: String?

    private let api = ApiService.shared

    var netWorthDollars: Double {
        Double(netWorth) / 100.0
    }

    var safeToSpendDollars: Double {
        Double(safeToSpend) / 100.0
    }

    var monthlyInflowDollars: Double {
        Double(monthlyInflow) / 100.0
    }

    var monthlyOutflowDollars: Double {
        Double(monthlyOutflow) / 100.0
    }

    var totalAssets: Int {
        accounts.filter { $0.balance > 0 }.reduce(0) { $0 + $1.balance }
    }

    var totalLiabilities: Int {
        abs(accounts.filter { $0.balance < 0 }.reduce(0) { $0 + $1.balance })
    }

    func loadDashboard() async {
        isLoading = true
        errorMessage = nil

        do {
            // Since we don't have a combined dashboard endpoint, we'll fetch separately
            accounts = try await api.getAccounts().map { acc in
                AccountWithBalance(
                    id: acc.id,
                    name: acc.name,
                    accountType: acc.accountType,
                    institution: acc.institution,
                    balance: 0 // We'll calculate this from transactions later
                )
            }

            // For now, set placeholder values
            netWorth = 0
            safeToSpend = 0
            monthlyInflow = 0
            monthlyOutflow = 0
            recentTransactions = []
            upcomingBills = []
            insights = []

        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }

    func refreshData() async {
        await loadDashboard()
    }
}