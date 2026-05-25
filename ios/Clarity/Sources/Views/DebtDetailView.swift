import SwiftUI

struct DebtDetailView: View {
    let debt: Debt
    @ObservedObject var viewModel: DebtsViewModel
    @Environment(\.dismiss) private var dismiss

    @State private var monthlyPayment: String = ""
    @State private var extraPayment: String = ""
    @State private var showingDelete = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 20) {
                    // Debt info cards
                    HStack(spacing: 12) {
                        StatCard2(title: "Balance", value: debt.formattedBalance, color: .red)
                        StatCard2(title: "Rate", value: debt.formattedInterestRate, color: .purple)
                    }
                    HStack(spacing: 12) {
                        StatCard2(title: "Min Payment", value: debt.formattedMinimumPayment, color: .orange)
                        StatCard2(title: "Original", value: String(format: "$%.2f", debt.initialAmountDollars), color: .secondary)
                    }

                    // Simulation section
                    VStack(alignment: .leading, spacing: 12) {
                        Text("Payoff Simulation")
                            .font(.headline)

                        HStack {
                            Text("$")
                            TextField("Monthly Payment", text: $monthlyPayment)
                                .keyboardType(.decimalPad)
                        }
                        .padding(12)
                        .background(Color(.systemGray6))
                        .cornerRadius(8)

                        HStack {
                            Text("$")
                            TextField("Extra Payment", text: $extraPayment)
                                .keyboardType(.decimalPad)
                        }
                        .padding(12)
                        .background(Color(.systemGray6))
                        .cornerRadius(8)

                        Button {
                            Task {
                                let mp = Double(monthlyPayment)
                                let ep = Double(extraPayment) ?? 0
                                await viewModel.loadProjection(debtId: debt.id, monthlyPayment: mp, extraPayment: ep)
                            }
                        } label: {
                            Text("Calculate").frame(maxWidth: .infinity)
                        }
                        .buttonStyle(.borderedProminent)
                    }
                    .padding()
                    .background(Color(.systemBackground))
                    .cornerRadius(12)
                    .shadow(color: .black.opacity(0.05), radius: 5, x: 0, y: 2)

                    // Projection results
                    if let proj = viewModel.projection {
                        VStack(alignment: .leading, spacing: 12) {
                            Text("Results").font(.headline)

                            HStack(spacing: 12) {
                                StatCard2(title: "Months", value: "\(proj.monthsToPayoff)", color: .blue)
                                StatCard2(title: "Payoff", value: formattedDate(proj.payoffDate), color: .green, small: true)
                            }
                            HStack(spacing: 12) {
                                StatCard2(title: "Total Interest", value: String(format: "$%.2f", proj.totalInterestDollars), color: .red)
                                StatCard2(title: "Total Cost", value: String(format: "$%.2f", proj.totalCostDollars), color: .orange)
                            }

                            // Schedule table
                            Text("Payment Schedule (first 12)")
                                .font(.subheadline).fontWeight(.medium)
                                .padding(.top, 4)

                            VStack(spacing: 0) {
                                HStack {
                                    Text("#").frame(width: 30, alignment: .leading)
                                    Text("Payment").frame(minWidth: 70, alignment: .trailing)
                                    Text("Interest").frame(minWidth: 70, alignment: .trailing)
                                    Text("Principal").frame(minWidth: 70, alignment: .trailing)
                                    Text("Balance").frame(minWidth: 70, alignment: .trailing)
                                }
                                .font(.caption2).fontWeight(.semibold)
                                .padding(.vertical, 6)

                                Divider()

                                ForEach(Array(proj.monthlySchedule.prefix(12)), id: \.month) { row in
                                    HStack {
                                        Text("\(row.month)").frame(width: 30, alignment: .leading)
                                        Text(String(format: "$%.0f", row.paymentDollars)).frame(minWidth: 70, alignment: .trailing)
                                        Text(String(format: "$%.0f", row.interestDollars)).frame(minWidth: 70, alignment: .trailing)
                                        Text(String(format: "$%.0f", row.principalDollars)).frame(minWidth: 70, alignment: .trailing)
                                        Text(String(format: "$%.0f", row.balanceDollars)).frame(minWidth: 70, alignment: .trailing)
                                    }
                                    .font(.system(size: 11))
                                    .padding(.vertical, 4)
                                    Divider()
                                }
                            }
                            .font(.caption)
                        }
                        .padding()
                        .background(Color(.systemBackground))
                        .cornerRadius(12)
                        .shadow(color: .black.opacity(0.05), radius: 5, x: 0, y: 2)
                    }
                }
                .padding()
            }
            .navigationTitle(debt.name)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .destructiveAction) {
                    Button(role: .destructive) {
                        showingDelete = true
                    } label: {
                        Image(systemName: "trash")
                    }
                }
            }
            .alert("Delete Debt?", isPresented: $showingDelete) {
                Button("Cancel", role: .cancel) {}
                Button("Delete", role: .destructive) {
                    Task {
                        _ = await viewModel.deleteDebt(id: debt.id)
                        dismiss()
                    }
                }
            } message: {
                Text("This will permanently delete this debt.")
            }
            .onAppear {
                monthlyPayment = String(format: "%.2f", debt.minimumPaymentDollars)
            }
        }
    }

    func formattedDate(_ date: Date) -> String {
        let f = DateFormatter()
        f.dateFormat = "MMM yyyy"
        return f.string(from: date)
    }
}

struct StatCard2: View {
    let title: String
    let value: String
    let color: Color
    var small: Bool = false

    var body: some View {
        VStack(spacing: 4) {
            Text(title).font(.caption).foregroundStyle(.secondary)
            Text(value)
                .font(small ? .caption : .subheadline)
                .fontWeight(.semibold)
                .foregroundStyle(color)
                .lineLimit(1)
                .minimumScaleFactor(0.7)
        }
        .frame(maxWidth: .infinity)
        .padding(12)
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(color: .black.opacity(0.05), radius: 5, x: 0, y: 2)
    }
}