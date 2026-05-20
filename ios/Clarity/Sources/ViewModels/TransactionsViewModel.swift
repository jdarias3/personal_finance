import Foundation

@MainActor
class TransactionsViewModel: ObservableObject {
    @Published var transactions: [Transaction] = []
    @Published var categories: [Category] = []
    @Published var isLoading = false
    @Published var errorMessage: String?
    @Published var selectedAccountId: UUID?
    @Published var selectedCategoryId: UUID?

    private let api = ApiService.shared

    var transactionsByDate: [String: [Transaction]] {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"

        var grouped: [String: [Transaction]] = [:]
        for transaction in transactions {
            let dateKey = formatter.string(from: transaction.date)
            if grouped[dateKey] == nil {
                grouped[dateKey] = []
            }
            grouped[dateKey]?.append(transaction)
        }
        return grouped
    }

    var sortedDates: [String] {
        transactionsByDate.keys.sorted(by: >)
    }

    func loadTransactions() async {
        isLoading = true
        errorMessage = nil

        do {
            transactions = try await api.getTransactions(
                accountId: selectedAccountId,
                categoryId: selectedCategoryId
            )
            categories = try await api.getCategories()
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }

    func createTransaction(
        accountId: UUID,
        type: TransactionType,
        amount: Double,
        date: Date,
        description: String,
        payee: String?,
        categoryId: UUID?,
        notes: String?
    ) async -> Bool {
        isLoading = true
        errorMessage = nil

        do {
            _ = try await api.createTransaction(
                accountId: accountId,
                transactionType: type,
                amount: amount,
                date: date,
                description: description,
                payee: payee,
                categoryId: categoryId,
                notes: notes
            )
            await loadTransactions()
            return true
        } catch {
            errorMessage = error.localizedDescription
            isLoading = false
            return false
        }
    }

    func deleteTransaction(id: UUID) async -> Bool {
        isLoading = true
        errorMessage = nil

        do {
            try await api.deleteTransaction(id: id)
            await loadTransactions()
            return true
        } catch {
            errorMessage = error.localizedDescription
            isLoading = false
            return false
        }
    }

    func createCategory(name: String) async -> Bool {
        do {
            _ = try await api.createCategory(name: name)
            await loadTransactions()
            return true
        } catch {
            errorMessage = error.localizedDescription
            return false
        }
    }
}