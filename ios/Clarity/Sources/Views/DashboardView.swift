import SwiftUI

struct DashboardView: View {
    @StateObject private var viewModel = DashboardViewModel()

    var body: some View {
        NavigationStack {
            ScrollView {
                if viewModel.isLoading {
                    ProgressView()
                        .padding()
                } else {
                    VStack(spacing: 20) {
                        // Net Worth Card
                        NetWorthCard(netWorth: viewModel.netWorthDollars)

                        // Quick Stats
                        HStack(spacing: 12) {
                            StatCard(
                                title: "Income",
                                value: viewModel.monthlyInflowDollars,
                                icon: "arrow.down.circle.fill",
                                color: .green
                            )

                            StatCard(
                                title: "Expenses",
                                value: viewModel.monthlyOutflowDollars,
                                icon: "arrow.up.circle.fill",
                                color: .red
                            )
                        }

                        // Safe to Spend
                        SafeToSpendCard(amount: viewModel.safeToSpendDollars)

                        // Accounts Overview
                        AccountsOverviewCard(accounts: viewModel.accounts)

                        // Recent Transactions
                        if !viewModel.recentTransactions.isEmpty {
                            RecentTransactionsCard(transactions: viewModel.recentTransactions)
                        }

                        // Insights
                        if !viewModel.insights.isEmpty {
                            InsightsCard(insights: viewModel.insights)
                        }
                    }
                    .padding()
                }
            }
            .navigationTitle("Dashboard")
            .refreshable {
                await viewModel.refreshData()
            }
            .task {
                await viewModel.loadDashboard()
            }
        }
    }
}

struct NetWorthCard: View {
    let netWorth: Double

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Net Worth")
                .font(.subheadline)
                .foregroundStyle(.secondary)

            Text(String(format: "$%.2f", netWorth))
                .font(.system(size: 32, weight: .bold))
                .foregroundStyle(netWorth >= 0 ? Color.primary : Color.red)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(color: .black.opacity(0.05), radius: 5, x: 0, y: 2)
    }
}

struct StatCard: View {
    let title: String
    let value: Double
    let icon: String
    let color: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Image(systemName: icon)
                    .foregroundStyle(color)
                Text(title)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }

            Text(String(format: "$%.2f", value))
                .font(.title2)
                .fontWeight(.semibold)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(color: .black.opacity(0.05), radius: 5, x: 0, y: 2)
    }
}

struct SafeToSpendCard: View {
    let amount: Double

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text("Safe to Spend")
                    .font(.headline)
                Spacer()
                Image(systemName: "sparkles")
                    .foregroundStyle(.yellow)
            }

            Text(String(format: "$%.2f", amount))
                .font(.title)
                .fontWeight(.bold)
                .foregroundStyle(.green)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(color: .black.opacity(0.05), radius: 5, x: 0, y: 2)
    }
}

struct AccountsOverviewCard: View {
    let accounts: [AccountWithBalance]

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("Accounts")
                    .font(.headline)
                Spacer()
                NavigationLink(destination: AccountsView()) {
                    Text("See All")
                        .font(.subheadline)
                }
            }

            if accounts.isEmpty {
                Text("No accounts yet")
                    .foregroundStyle(.secondary)
                    .padding()
            } else {
                let displayAccounts = Array(accounts.prefix(3))
                ForEach(displayAccounts, id: \.id) { account in
                    HStack {
                        Image(systemName: account.typeEnum.icon)
                            .foregroundStyle(.blue)
                            .frame(width: 30)

                        VStack(alignment: .leading) {
                            Text(account.name)
                                .font(.subheadline)
                            Text(account.institution ?? account.accountType)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }

                        Spacer()

                        Text(account.formattedBalance)
                            .font(.subheadline)
                            .fontWeight(.medium)
                            .foregroundStyle(account.balance >= 0 ? Color.primary : Color.red)
                    }
                }
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(color: .black.opacity(0.05), radius: 5, x: 0, y: 2)
    }
}

struct RecentTransactionsCard: View {
    let transactions: [Transaction]

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("Recent Transactions")
                    .font(.headline)
                Spacer()
                NavigationLink(destination: TransactionsView()) {
                    Text("See All")
                        .font(.subheadline)
                }
            }

            ForEach(transactions.prefix(5)) { transaction in
                HStack {
                    VStack(alignment: .leading) {
                        Text(transaction.description)
                            .font(.subheadline)
                        if let payee = transaction.payee {
                            Text(payee)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }

                    Spacer()

                    Text(transaction.formattedAmount)
                        .font(.subheadline)
                        .fontWeight(.medium)
                        .foregroundStyle(transaction.typeEnum == .inflow ? .green : .red)
                }
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(color: .black.opacity(0.05), radius: 5, x: 0, y: 2)
    }
}

struct InsightsCard: View {
    let insights: [Insight]

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Insights")
                .font(.headline)

            ForEach(insights, id: \.message) { insight in
                HStack(alignment: .top, spacing: 8) {
                    Image(systemName: insight.type == "info" ? "info.circle.fill" : "exclamationmark.circle.fill")
                        .foregroundStyle(insight.type == "info" ? .blue : .orange)

                    Text(insight.message)
                        .font(.subheadline)
                }
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(color: .black.opacity(0.05), radius: 5, x: 0, y: 2)
    }
}

#Preview {
    DashboardView()
}