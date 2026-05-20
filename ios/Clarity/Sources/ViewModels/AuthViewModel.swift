import Foundation

@MainActor
class AuthViewModel: ObservableObject {
    @Published var isAuthenticated = false
    @Published var isLoading = false
    @Published var errorMessage: String?
    @Published var currentUser: User?

    private let api = ApiService.shared
    private let tokenKey = "authToken"

    init() {
        // Check for stored token on app launch
        if let token = UserDefaults.standard.string(forKey: tokenKey) {
            api.setAuthToken(token)
            isAuthenticated = true
            Task {
                await loadCurrentUser()
            }
        }
    }

    func login(email: String, password: String) async {
        isLoading = true
        errorMessage = nil

        do {
            let response = try await api.login(email: email, password: password)
            api.setAuthToken(response.accessToken)
            UserDefaults.standard.set(response.accessToken, forKey: tokenKey)
            isAuthenticated = true
            await loadCurrentUser()
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }

    func register(name: String, email: String, password: String) async {
        isLoading = true
        errorMessage = nil

        do {
            _ = try await api.register(name: name, email: email, password: password)
            // After register, login automatically
            await login(email: email, password: password)
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }

    func logout() {
        api.setAuthToken(nil)
        UserDefaults.standard.removeObject(forKey: tokenKey)
        isAuthenticated = false
        currentUser = nil
    }

    private func loadCurrentUser() async {
        // For now, we'll just set a placeholder since there's no /me endpoint
        // In a real app, you'd have an endpoint to get current user
        currentUser = nil
    }
}