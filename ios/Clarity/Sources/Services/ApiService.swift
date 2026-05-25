import Foundation

enum ApiError: Error, LocalizedError {
    case invalidURL
    case noData
    case decodingError(Error)
    case serverError(Int)
    case networkError(Error)

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid URL"
        case .noData:
            return "No data received"
        case .decodingError(let error):
            return "Decoding error: \(error.localizedDescription)"
        case .serverError(let code):
            return "Server error: \(code)"
        case .networkError(let error):
            return "Network error: \(error.localizedDescription)"
        }
    }
}

class ApiService {
    static let shared = ApiService()

    private let baseURL: String
    private var authToken: String?
    private let decoder: JSONDecoder
    private let encoder: JSONEncoder

    private init() {
        // Change this to your deployed Render URL
        self.baseURL = "https://clarity-ygsw.onrender.com"

        self.decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601

        self.encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
    }

    func setAuthToken(_ token: String?) {
        self.authToken = token
    }

    private var headers: [String: String] {
        var h = ["Content-Type": "application/json"]
        if let token = authToken {
            h["Authorization"] = "Bearer \(token)"
        }
        return h
    }

    // MARK: - Auth

    func login(email: String, password: String) async throws -> LoginResponse {
        let body = "email=\(email.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? "")&password=\(password.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? "")"
        return try await postForm("/api/login", body: body)
    }

    func register(name: String, email: String, password: String) async throws -> User {
        let body = "name=\(name.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? "")&email=\(email.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? "")&password=\(password.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? "")"
        return try await postForm("/api/register", body: body)
    }

    // MARK: - Dashboard

    func getDashboard() async throws -> DashboardData {
        return try await get("/dashboard")
    }

    // MARK: - Accounts

    func getAccounts() async throws -> [Account] {
        return try await get("/accounts")
    }

    func createAccount(name: String, accountType: AccountType, institution: String?) async throws -> Account {
        let request = CreateAccountRequest(name: name, accountType: accountType.rawValue, institution: institution)
        return try await post("/accounts/new", body: request)
    }

    func deleteAccount(id: UUID) async throws {
        let _: EmptyResponse = try await post("/accounts/\(id.uuidString)/delete", body: EmptyBody())
    }

    // MARK: - Transactions

    func getTransactions(accountId: UUID? = nil, categoryId: UUID? = nil) async throws -> [Transaction] {
        var queryItems: [String] = []
        if let accountId = accountId {
            queryItems.append("account_id=\(accountId.uuidString)")
        }
        if let categoryId = categoryId {
            queryItems.append("category_id=\(categoryId.uuidString)")
        }
        let query = queryItems.isEmpty ? "" : "?" + queryItems.joined(separator: "&")
        return try await get("/transactions\(query)")
    }

    func createTransaction(
        accountId: UUID,
        transactionType: TransactionType,
        amount: Double,
        date: Date,
        description: String,
        payee: String?,
        categoryId: UUID?,
        notes: String?
    ) async throws -> Transaction {
        let request = CreateTransactionRequest(
            accountId: accountId,
            transactionType: transactionType.rawValue,
            amount: amount,
            date: date,
            description: description,
            payee: payee,
            categoryId: categoryId,
            notes: notes
        )
        return try await post("/transactions/new", body: request)
    }

    func deleteTransaction(id: UUID) async throws {
        let _: EmptyResponse = try await post("/transactions/\(id.uuidString)/delete", body: EmptyBody())
    }

    // MARK: - Categories

    func getCategories() async throws -> [Category] {
        return try await get("/categories")
    }

    func createCategory(name: String, icon: String? = nil, color: String? = nil) async throws -> Category {
        let request = CreateCategoryRequest(name: name, icon: icon, color: color)
        return try await post("/categories/new", body: request)
    }

    // MARK: - Debts

    func getDebts(page: Int = 1) async throws -> [Debt] {
        let response: DebtsResponse = try await get("/api/debts")
        return response.debts
    }

    func getDebtSummary() async throws -> DebtSummary {
        let response: DebtsResponse = try await get("/api/debts")
        return response.summary
    }

    func createDebt(name: String, initialAmount: Double, currentBalance: Double, interestRate: Double, minimumPayment: Double, dueDay: Int?, accountId: UUID?) async throws -> Debt {
        var body = "name=\(name.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? "")&initial_amount=\(initialAmount)&current_balance=\(currentBalance)&interest_rate=\(interestRate)&minimum_payment=\(minimumPayment)"
        if let dueDay = dueDay { body += "&due_day=\(dueDay)" }
        if let accountId = accountId { body += "&account_id=\(accountId.uuidString)" }
        let _: EmptyResponse = try await postForm("/api/debts/new", body: body)
        return try await getDebts().first ?? Debt(
            id: UUID(), userId: UUID(), accountId: nil, name: name,
            initialAmountCents: Int(initialAmount), currentBalanceCents: Int(currentBalance),
            interestRate: Int(interestRate), minimumPaymentCents: Int(minimumPayment),
            dueDay: dueDay, createdAt: Date(), updatedAt: Date()
        )
    }

    func deleteDebt(id: UUID) async throws {
        let _: EmptyResponse = try await post("/api/debts/\(id.uuidString)/delete", body: EmptyBody())
    }

    func getPayoffProjection(debtId: UUID, monthlyPayment: Double? = nil, extraPayment: Double = 0) async throws -> PayoffProjection {
        var body = "extra_payment=\(extraPayment)"
        if let mp = monthlyPayment { body += "&monthly_payment=\(mp)" }
        return try await postForm("/api/debts/\(debtId.uuidString)/project", body: body)
    }

    private func get<T: Decodable>(_ path: String) async throws -> T {
        guard let url = URL(string: baseURL + path) else {
            throw ApiError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        for (key, value) in headers {
            request.setValue(value, forHTTPHeaderField: key)
        }

        do {
            let (data, response) = try await URLSession.shared.data(for: request)

            guard let httpResponse = response as? HTTPURLResponse else {
                throw ApiError.noData
            }

            guard (200...299).contains(httpResponse.statusCode) else {
                throw ApiError.serverError(httpResponse.statusCode)
            }

            do {
                return try decoder.decode(T.self, from: data)
            } catch {
                throw ApiError.decodingError(error)
            }
        } catch let error as ApiError {
            throw error
        } catch {
            throw ApiError.networkError(error)
        }
    }

    private func post<T: Decodable, B: Encodable>(_ path: String, body: B) async throws -> T {
        guard let url = URL(string: baseURL + path) else {
            throw ApiError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        for (key, value) in headers {
            request.setValue(value, forHTTPHeaderField: key)
        }
        request.httpBody = try encoder.encode(body)

        do {
            let (data, response) = try await URLSession.shared.data(for: request)

            guard let httpResponse = response as? HTTPURLResponse else {
                throw ApiError.noData
            }

            guard (200...299).contains(httpResponse.statusCode) else {
                throw ApiError.serverError(httpResponse.statusCode)
            }

            if T.self == EmptyResponse.self {
                return EmptyResponse() as! T
            }

            do {
                return try decoder.decode(T.self, from: data)
            } catch {
                throw ApiError.decodingError(error)
            }
        } catch let error as ApiError {
            throw error
        } catch {
            throw ApiError.networkError(error)
        }
    }

    private func postForm<T: Decodable>(_ path: String, body: String) async throws -> T {
        guard let url = URL(string: baseURL + path) else {
            throw ApiError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")
        if let token = authToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        request.httpBody = body.data(using: .utf8)

        do {
            let (data, response) = try await URLSession.shared.data(for: request)

            guard let httpResponse = response as? HTTPURLResponse else {
                throw ApiError.noData
            }

            guard (200...299).contains(httpResponse.statusCode) else {
                throw ApiError.serverError(httpResponse.statusCode)
            }

            do {
                return try decoder.decode(T.self, from: data)
            } catch {
                throw ApiError.decodingError(error)
            }
        } catch let error as ApiError {
            throw error
        } catch {
            throw ApiError.networkError(error)
        }
    }
}

struct DebtsResponse: Decodable {
    let debts: [Debt]
    let summary: DebtSummary
}

struct EmptyBody: Encodable {}
struct EmptyResponse: Decodable {}
