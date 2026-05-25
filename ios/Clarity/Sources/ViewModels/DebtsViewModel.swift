import Foundation

@MainActor
class DebtsViewModel: ObservableObject {
    @Published var debts: [Debt] = []
    @Published var summary: DebtSummary?
    @Published var projection: PayoffProjection?
    @Published var isLoading = false
    @Published var errorMessage: String?

    private let api = ApiService.shared

    var totalDebtDollars: Double {
        guard let s = summary else { return 0 }
        return s.totalDebtDollars
    }

    var totalMinPaymentDollars: Double {
        guard let s = summary else { return 0 }
        return s.totalMinimumPaymentDollars
    }

    var avgRateString: String {
        guard let s = summary else { return "0%" }
        return String(format: "%.2f%%", s.avgInterestRatePercent)
    }

    func loadDebts() async {
        isLoading = true
        errorMessage = nil
        do {
            async let debtsTask = api.getDebts()
            async let summaryTask = api.getDebtSummary()
            (debts, summary) = try await (debtsTask, summaryTask)
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    func createDebt(name: String, initialAmount: Double, currentBalance: Double, interestRate: Double, minimumPayment: Double, dueDay: Int?, accountId: UUID?) async -> Bool {
        isLoading = true
        errorMessage = nil
        do {
            _ = try await api.createDebt(name: name, initialAmount: initialAmount, currentBalance: currentBalance, interestRate: interestRate, minimumPayment: minimumPayment, dueDay: dueDay, accountId: accountId)
            await loadDebts()
            return true
        } catch {
            errorMessage = error.localizedDescription
            isLoading = false
            return false
        }
    }

    func deleteDebt(id: UUID) async -> Bool {
        isLoading = true
        errorMessage = nil
        do {
            try await api.deleteDebt(id: id)
            await loadDebts()
            return true
        } catch {
            errorMessage = error.localizedDescription
            isLoading = false
            return false
        }
    }

    func loadProjection(debtId: UUID, monthlyPayment: Double? = nil, extraPayment: Double = 0) async {
        isLoading = true
        errorMessage = nil
        do {
            projection = try await api.getPayoffProjection(debtId: debtId, monthlyPayment: monthlyPayment, extraPayment: extraPayment)
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }
}