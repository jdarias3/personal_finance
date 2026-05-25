import SwiftUI

struct DebtsView: View {
    @StateObject private var viewModel = DebtsViewModel()
    @State private var showingAddDebt = false
    @State private var selectedDebt: Debt?

    var body: some View {
        NavigationStack {
            ScrollView {
                if viewModel.isLoading {
                    ProgressView().padding()
                } else {
                    VStack(spacing: 20) {
                        // Summary cards
                        HStack(spacing: 12) {
                            DebtStatCard(title: "Total Debt", amount: viewModel.totalDebtDollars, color: .red)
                            DebtStatCard(title: "Min Payment", amount: viewModel.totalMinPaymentDollars, color: .orange)
                        }

                        HStack(spacing: 12) {
                            VStack(spacing: 4) {
                                Text("Avg Interest")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                                Text(viewModel.avgRateString)
                                    .font(.title3).fontWeight(.bold)
                                    .foregroundStyle(.purple)
                            }
                            .frame(maxWidth: .infinity)
                            .padding()
                            .background(Color(.systemBackground))
                            .cornerRadius(12)
                            .shadow(color: .black.opacity(0.05), radius: 5, x: 0, y: 2)

                            VStack(spacing: 4) {
                                Text("Debt Count")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                                Text("\(viewModel.summary?.debtCount ?? 0)")
                                    .font(.title3).fontWeight(.bold)
                            }
                            .frame(maxWidth: .infinity)
                            .padding()
                            .background(Color(.systemBackground))
                            .cornerRadius(12)
                            .shadow(color: .black.opacity(0.05), radius: 5, x: 0, y: 2)
                        }

                        if viewModel.debts.isEmpty {
                            emptyState
                        } else {
                            // Debt list
                            VStack(alignment: .leading, spacing: 0) {
                                Text("Your Debts")
                                    .font(.headline)
                                    .padding(.horizontal)
                                    .padding(.bottom, 8)

                                ForEach(viewModel.debts) { debt in
                                    DebtRow(debt: debt)
                                        .onTapGesture {
                                            selectedDebt = debt
                                        }
                                }
                            }
                        }
                    }
                    .padding()
                }
            }
            .navigationTitle("Debts")
            .toolbar {
                ToolbarItem(placement: .primaryAction) {
                    Button { showingAddDebt = true } label: {
                        Image(systemName: "plus")
                    }
                }
            }
            .sheet(isPresented: $showingAddDebt) {
                DebtFormView(viewModel: viewModel)
            }
            .sheet(item: $selectedDebt) { debt in
                DebtDetailView(debt: debt, viewModel: viewModel)
            }
            .task { await viewModel.loadDebts() }
        }
    }

    var emptyState: some View {
        VStack(spacing: 16) {
            Image(systemName: "creditcard.and.123")
                .font(.system(size: 50)).foregroundStyle(.secondary)
            Text("No debts tracked").font(.headline)
            Button("Add Your First Debt") { showingAddDebt = true }
                .buttonStyle(.borderedProminent)
        }
        .padding(.top, 40)
    }
}

struct DebtStatCard: View {
    let title: String
    let amount: Double
    let color: Color

    var body: some View {
        VStack(spacing: 4) {
            Text(title).font(.caption).foregroundStyle(.secondary)
            Text(String(format: "$%.2f", amount))
                .font(.title3).fontWeight(.bold)
                .foregroundStyle(color)
        }
        .frame(maxWidth: .infinity)
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(color: .black.opacity(0.05), radius: 5, x: 0, y: 2)
    }
}

struct DebtRow: View {
    let debt: Debt

    var body: some View {
        VStack(spacing: 8) {
            HStack {
                Image(systemName: debt.icon)
                    .font(.title2).foregroundStyle(.red)
                    .frame(width: 36)

                VStack(alignment: .leading, spacing: 2) {
                    Text(debt.name).font(.subheadline).fontWeight(.medium)
                    HStack(spacing: 4) {
                        Text(debt.formattedInterestRate).font(.caption).foregroundStyle(.secondary)
                        Text("·").font(.caption).foregroundStyle(.secondary)
                        Text("\(debt.formattedMinimumPayment)/mo").font(.caption).foregroundStyle(.secondary)
                    }
                }

                Spacer()

                VStack(alignment: .trailing, spacing: 2) {
                    Text(debt.formattedBalance)
                        .font(.subheadline).fontWeight(.semibold)
                    if debt.dueDay != nil {
                        Text("Due day \(debt.dueDay!)").font(.caption2).foregroundStyle(.secondary)
                    }
                }
            }

            // Progress bar
            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    Rectangle()
                        .fill(Color(.systemGray5))
                        .frame(height: 6)
                        .cornerRadius(3)
                    Rectangle()
                        .fill(debt.progressPercent > 0.5 ? Color.green : Color.orange)
                        .frame(width: geo.size.width * debt.progressPercent, height: 6)
                        .cornerRadius(3)
                }
            }
            .frame(height: 6)
        }
        .padding(.horizontal)
        .padding(.vertical, 12)
        .background(Color(.systemBackground))
    }
}

#Preview {
    DebtsView()
}