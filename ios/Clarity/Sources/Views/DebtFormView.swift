import SwiftUI

struct DebtFormView: View {
    @ObservedObject var viewModel: DebtsViewModel
    @Environment(\.dismiss) private var dismiss

    @State private var name = ""
    @State private var initialAmount = ""
    @State private var currentBalance = ""
    @State private var interestRate = ""
    @State private var minimumPayment = ""
    @State private var dueDay = ""

    var isValid: Bool {
        !name.isEmpty && !initialAmount.isEmpty && !currentBalance.isEmpty && !interestRate.isEmpty && !minimumPayment.isEmpty
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("Debt Details") {
                    TextField("Name", text: $name)
                        .placeholder(when: name.isEmpty) { Text("e.g., Chase Credit Card") }

                    HStack {
                        Text("$")
                        TextField("Original Balance", text: $initialAmount)
                            .keyboardType(.decimalPad)
                    }

                    HStack {
                        Text("$")
                        TextField("Current Balance", text: $currentBalance)
                            .keyboardType(.decimalPad)
                    }

                    HStack {
                        TextField("Interest Rate (%)", text: $interestRate)
                            .keyboardType(.decimalPad)
                        Text("%")
                    }

                    HStack {
                        Text("$")
                        TextField("Minimum Payment", text: $minimumPayment)
                            .keyboardType(.decimalPad)
                    }
                }

                Section("Optional") {
                    TextField("Due Day of Month (1-31)", text: $dueDay)
                        .keyboardType(.numberPad)
                }

                if let error = viewModel.errorMessage {
                    Text(error).font(.caption).foregroundStyle(.red)
                }
            }
            .navigationTitle("Add Debt")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        Task {
                            let success = await viewModel.createDebt(
                                name: name,
                                initialAmount: Double(initialAmount) ?? 0,
                                currentBalance: Double(currentBalance) ?? 0,
                                interestRate: Double(interestRate) ?? 0,
                                minimumPayment: Double(minimumPayment) ?? 0,
                                dueDay: Int(dueDay),
                                accountId: nil
                            )
                            if success { dismiss() }
                        }
                    }
                    .disabled(!isValid)
                }
            }
        }
    }
}

extension View {
    func placeholder<Content: View>(when shouldShow: Bool, @ViewBuilder content: () -> Content) -> some View {
        ZStack(alignment: .leading) {
            self
            if shouldShow { content().foregroundStyle(.secondary) }
        }
    }
}