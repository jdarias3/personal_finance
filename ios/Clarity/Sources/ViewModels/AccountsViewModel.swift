import Foundation

@MainActor
class AccountsViewModel: ObservableObject {
    @Published var accounts: [Account] = []
    @Published var isLoading = false
    @Published var errorMessage: String?

    private let api = ApiService.shared

    func loadAccounts() async {
        isLoading = true
        errorMessage = nil

        do {
            accounts = try await api.getAccounts()
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }

    func createAccount(name: String, accountType: AccountType, institution: String?) async -> Bool {
        isLoading = true
        errorMessage = nil

        do {
            _ = try await api.createAccount(name: name, accountType: accountType, institution: institution)
            await loadAccounts()
            return true
        } catch {
            errorMessage = error.localizedDescription
            isLoading = false
            return false
        }
    }

    func deleteAccount(id: UUID) async -> Bool {
        isLoading = true
        errorMessage = nil

        do {
            try await api.deleteAccount(id: id)
            await loadAccounts()
            return true
        } catch {
            errorMessage = error.localizedDescription
            isLoading = false
            return false
        }
    }
}