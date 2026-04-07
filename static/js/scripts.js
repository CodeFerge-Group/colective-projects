document.addEventListener('DOMContentLoaded', function() {
    console.log("Scripts MS Eventos Ativos");

    // Máscara Automática para Telefone de Angola
    const telInput = document.querySelector('input[name="telefone"]');
    if (telInput) {
        telInput.addEventListener('input', function(e) {
            let value = e.target.value.replace(/\D/g, ''); // Remove tudo que não é número

            if (!e.target.value.startsWith('+244')) {
                e.target.value = '+244 ';
            }

            // Formata: +244 9XX XXX XXX
            if (value.length > 3) {
                let formatted = '+244 ' + value.substring(3, 6);
                if (value.length > 6) formatted += ' ' + value.substring(6, 9);
                if (value.length > 9) formatted += ' ' + value.substring(9, 12);
                e.target.value = formatted;
            }
        });
    }

    // Validação de Data (Respeitando seu Trigger MySQL)
    const dateInput = document.querySelector('input[name="datanasc"]');
    if (dateInput) {
        dateInput.addEventListener('change', function() {
            const dataSelecionada = new Date(this.value);
            const hoje = new Date();
            if (dataSelecionada >= hoje) {
                alert("Erro: A data de nascimento não pode ser hoje ou no futuro!");
                this.value = '';
            }
        });
    }
});