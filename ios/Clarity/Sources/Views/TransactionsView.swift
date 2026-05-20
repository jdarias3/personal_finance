import SwiftUI

struct TransactionsView: View {
    @StateObject private var viewModel = TransactionsViewModel()
    @State private var showingAddTransaction = false
    @State private var showingAddCategory = false

    var body: some View {
        NavigationStack {
            ScrollView {
                if viewModel.isLoading {
                    ProgressView()
                        .padding()
                } else {
                    VStack(spacing: 0) {
                        // Filters
                        FiltersSection(
                            accounts: [],  // Would need to pass accounts
                            categories: viewModel.categories,
                            selectedAccountId: $viewModel.selectedAccountId,
                            selectedCategoryId: $viewModel.selectedCategoryId,
                            onApply: {
                                Task {
                                    await viewModel.loadTransactions()
                                }
                            }
                        )

                        // Transactions by date
                        if viewModel.transactions.isEmpty {
                            VStack(spacing: 16) {
                                Image(systemName: "list.bullet.rectangle")
                                    .font(.system(size: 50))
                                    .foregroundStyle(.secondary)
                                Text("No transactions yet")
                                    .font(.headline)
                                Button("Add Transaction") {
                                    showingAddTransaction = true
                                }
                                .buttonStyle(.borderedProminent)
                            }
                            .padding(.top, 40)
                        } else {
                            ForEach(viewModel.sortedDates, id: \.self) { date in
                                DateSection(
                                    date: date,
                                    transactions: viewModel.transactionsByDate[date] ?? [],
                                    onDelete: { id in
                                        Task {
                                            _ = await viewModel.deleteTransaction(id: id)
                                        }
                                    }
                                )
                            }
                        }
                    }
                }
            }
            .navigationTitle("Transactions")
            .toolbar {
                ToolbarItem(placement: .primaryAction) {
                    Menu {
                        Button {
                            showingAddTransaction = true
                        } label: {
                            Label("Add Transaction", systemImage: "plus")
                        }

                        Button {
                            showingAddCategory = true
                        } label: {
                            Label("Add Category", systemImage: "folder.badge.plus")
                        }
                    } label: {
                        Image(systemName: "plus")
                    }
                }
            }
            .sheet(isPresented: $showingAddTransaction) {
                AddTransactionView(viewModel: viewModel)
            }
            .sheet(isPresented: $showingAddCategory) {
                AddCategoryView { name in
                    Task {
                        _ = await viewModel.createCategory(name: name)
                    }
                }
            }
            .task {
                await viewModel.loadTransactions()
            }
        }
    }
}

struct FiltersSection: View {
    let accounts: [Account]
    let categories: [Category]
    @Binding var selectedAccountId: UUID?
    @Binding var selectedCategoryId: UUID?
    let onApply: () -> Void

    var body: some View {
        VStack(spacing: 12) {
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    // Account filter
                    if !accounts.isEmpty {
                        Menu {
                            Button("All Accounts") { selectedAccountId = nil }
                            ForEach(accounts) { account in
                                Button(account.name) { selectedAccountId = account.id }
                            }
                        } label: {
                            FilterChip(
                                title: selectedAccountId != nil ? "Account" : "All Accounts",
                                isActive: selectedAccountId != nil
                            )
                        }
                    }

                    // Category filter
                    if !categories.isEmpty {
                        Menu {
                            Button("All Categories") { selectedCategoryId = nil }
                            ForEach(categories) { category in
                                Button(category.name) { selectedCategoryId = category.id }
                            }
                        } label: {
                            FilterChip(
                                title: selectedCategoryId != nil ? "Category" : "All Categories",
                                isActive: selectedCategoryId != nil
                            )
                        }
                    }
                }
            }
        }
        .padding()
        .background(Color(.systemBackground))
    }
}

struct FilterChip: View {
    let title: String
    let isActive: Bool

    var body: some View {
        HStack(spacing: 4) {
            Text(title)
            Image(systemName: "chevron.down")
                .font(.caption)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background(isActive ? Color.blue.opacity(0.1) : Color(.systemGray6))
        .foregroundStyle(isActive ? .blue : .primary)
        .cornerRadius(20)
    }
}

struct DateSection: View {
    let date: String
    let transactions: [Transaction]
    let onDelete: (UUID) -> Void

    var formattedDate: String {
        let parts = date.split(separator: "-")
        if parts.count == 3 {
            return "\(parts[1])/\(parts[2])/\(parts[0])"
        }
        return date
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            Text(formattedDate)
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .padding(.horizontal)
                .padding(.vertical, 8)

            ForEach(transactions) { transaction in
                TransactionRow(transaction: transaction) {
                    onDelete(transaction.id)
                }
                Divider()
            }
        }
    }
}

struct TransactionRow: View {
    let transaction: Transaction
    let onDelete: () -> Void

    var body: some View {
        HStack(spacing: 12) {
            VStack(alignment: .leading, spacing: 4) {
                Text(transaction.description)
                    .font(.subheadline)
                HStack(spacing: 4) {
                    if let payee = transaction.payee {
                        Text(payee)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                    if let category = transaction.category {
                        Text("·")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                        Text(category)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
            }

            Spacer()

            Text(transaction.formattedAmount)
                .font(.subheadline)
                .fontWeight(.medium)
                .foregroundStyle(transaction.typeEnum == .inflow ? .green : .red)
        }
        .padding(.horizontal)
        .padding(.vertical, 12)
    }
}

struct AddTransactionView: View {
    @ObservedObject var viewModel: TransactionsViewModel
    @Environment(\.dismiss) private var dismiss

    @State private var selectedAccountId: UUID?
    @State private var transactionType: TransactionType = .outflow
    @State private var amount = ""
    @State private var date = Date()
    @State private var description = ""
    @State private var payee = ""
    @State private var selectedCategoryId: UUID?
    @State private var notes = ""
    @State private var showingNewCategory = false
    @State private var newCategoryName = ""

    var isValid: Bool {
        selectedAccountId != nil && !amount.isEmpty && !description.isEmpty
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("Details") {
                    Picker("Type", selection: $transactionType) {
                        Text("Expense").tag(TransactionType.outflow)
                        Text("Income").tag(TransactionType.inflow)
                    }
                    .pickerStyle(.segmented)

                    TextField("Amount", text: $amount)
                        .keyboardType(.decimalPad)

                    TextField("Description", text: $description)

                    DatePicker("Date", selection: $date, displayedComponents: .date)
                }

                Section("Account") {
                    Picker("Account", selection: $selectedAccountId) {
                        Text("Select Account").tag(nil as UUID?)
                        // Would need accounts passed in
                    }
                }

                Section("Category") {
                    Picker("Category", selection: $selectedCategoryId) {
                        Text("None").tag(nil as UUID?)
                        ForEach(viewModel.categories) { category in
                            Text(category.name).tag(category.id as UUID?)
                        }
                    }

                    Button {
                        showingNewCategory = true
                    } label: {
                        Label("New Category", systemImage: "plus")
                    }
                }

                Section("Optional") {
                    TextField("Payee", text: $payee)
                    TextField("Notes", text: $notes)
                }
            }
            .navigationTitle("Add Transaction")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        Task {
                            if let accountId = selectedAccountId,
                               let amountDouble = Double(amount) {
                                _ = await viewModel.createTransaction(
                                    accountId: accountId,
                                    type: transactionType,
                                    amount: amountDouble,
                                    date: date,
                                    description: description,
                                    payee: payee.isEmpty ? nil : payee,
                                    categoryId: selectedCategoryId,
                                    notes: notes.isEmpty ? nil : notes
                                )
                                dismiss()
                            }
                        }
                    }
                    .disabled(!isValid)
                }
            }
            .alert("New Category", isPresented: $showingNewCategory) {
                TextField("Category Name", text: $newCategoryName)
                Button("Cancel", role: .cancel) {}
                Button("Create") {
                    Task {
                        _ = await viewModel.createCategory(name: newCategoryName)
                    }
                }
            }
        }
    }
}

struct AddCategoryView: View {
    let onSave: (String) -> Void
    @Environment(\.dismiss) private var dismiss
    @State private var name = ""

    var body: some View {
        NavigationStack {
            Form {
                TextField("Category Name", text: $name)
            }
            .navigationTitle("New Category")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        onSave(name)
                        dismiss()
                    }
                    .disabled(name.isEmpty)
                }
            }
        }
    }
}

#Preview {
    TransactionsView()
}