import SwiftUI

struct AccountsView: View {
    @StateObject private var viewModel = AccountsViewModel()
    @State private var showingAddAccount = false

    var totalAssets: Int {
        viewModel.accounts.filter { $0.balance > 0 }.reduce(0) { $0 + $1.balance }
    }

    var totalLiabilities: Int {
        abs(viewModel.accounts.filter { $0.balance < 0 }.reduce(0) { $0 + $1.balance })
    }

    var netWorth: Int {
        totalAssets - totalLiabilities
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                if viewModel.isLoading {
                    ProgressView()
                        .padding()
                } else {
                    VStack(spacing: 20) {
                        // Summary
                        HStack(spacing: 16) {
                            SummaryItem(title: "Assets", amount: totalAssets, color: .green)
                            SummaryItem(title: "Liabilities", amount: totalLiabilities, color: .red)
                            SummaryItem(title: "Net Worth", amount: netWorth, color: .blue)
                        }
                        .padding()
                        .background(Color(.systemBackground))
                        .cornerRadius(12)
                        .shadow(color: .black.opacity(0.05), radius: 5, x: 0, y: 2)

                        // Accounts List
                        if viewModel.accounts.isEmpty {
                            VStack(spacing: 16) {
                                Image(systemName: "creditcard")
                                    .font(.system(size: 50))
                                    .foregroundStyle(.secondary)
                                Text("No accounts yet")
                                    .font(.headline)
                                Button("Add Account") {
                                    showingAddAccount = true
                                }
                                .buttonStyle(.borderedProminent)
                            }
                            .padding(.top, 40)
                        } else {
                            ForEach(viewModel.accounts) { account in
                                AccountRow(account: account) {
                                    Task {
                                        _ = await viewModel.deleteAccount(id: account.id)
                                    }
                                }
                            }
                        }

                        if let error = viewModel.errorMessage {
                            Text(error)
                                .font(.caption)
                                .foregroundStyle(.red)
                        }
                    }
                    .padding()
                }
            }
            .navigationTitle("Accounts")
            .toolbar {
                ToolbarItem(placement: .primaryAction) {
                    Button {
                        showingAddAccount = true
                    } label: {
                        Image(systemName: "plus")
                    }
                }
            }
            .sheet(isPresented: $showingAddAccount) {
                AddAccountView(viewModel: viewModel)
            }
            .task {
                await viewModel.loadAccounts()
            }
        }
    }
}

struct SummaryItem: View {
    let title: String
    let amount: Int
    let color: Color

    var amountDollars: Double {
        Double(amount) / 100.0
    }

    var body: some View {
        VStack(spacing: 4) {
            Text(title)
                .font(.caption)
                .foregroundStyle(.secondary)
            Text(String(format: "$%.2f", amountDollars))
                .font(.subheadline)
                .fontWeight(.semibold)
                .foregroundStyle(color)
        }
        .frame(maxWidth: .infinity)
    }
}

struct AccountRow: View {
    let account: Account
    let onDelete: () -> Void

    var body: some View {
        HStack(spacing: 16) {
            Image(systemName: account.typeEnum.icon)
                .font(.title2)
                .foregroundStyle(.blue)
                .frame(width: 40)

            VStack(alignment: .leading, spacing: 4) {
                Text(account.name)
                    .font(.headline)
                Text(account.institution ?? account.typeEnum.displayName)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }

            Spacer()

            Text("$0.00")
                .font(.headline)
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(color: .black.opacity(0.05), radius: 5, x: 0, y: 2)
    }
}

struct AddAccountView: View {
    @ObservedObject var viewModel: AccountsViewModel
    @Environment(\.dismiss) private var dismiss

    @State private var name = ""
    @State private var selectedType: AccountType = .checking
    @State private var institution = ""
    @State private var showingDeleteConfirmation = false

    var body: some View {
        NavigationStack {
            Form {
                Section("Account Details") {
                    TextField("Account Name", text: $name)
                    Picker("Type", selection: $selectedType) {
                        ForEach(AccountType.allCases, id: \.self) { type in
                            Label(type.displayName, systemImage: type.icon)
                                .tag(type)
                        }
                    }
                    TextField("Institution (optional)", text: $institution)
                }

                Section {
                    Button(role: .destructive) {
                        showingDeleteConfirmation = true
                    } label: {
                        Text("Delete Account")
                    }
                }
            }
            .navigationTitle("Add Account")
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
                            let success = await viewModel.createAccount(
                                name: name,
                                accountType: selectedType,
                                institution: institution.isEmpty ? nil : institution
                            )
                            if success {
                                dismiss()
                            }
                        }
                    }
                    .disabled(name.isEmpty)
                }
            }
            .alert("Delete Account?", isPresented: $showingDeleteConfirmation) {
                Button("Cancel", role: .cancel) {}
                Button("Delete", role: .destructive) {
                    // Handle delete
                }
            } message: {
                Text("This will delete the account and all its transactions.")
            }
        }
    }
}

#Preview {
    AccountsView()
}