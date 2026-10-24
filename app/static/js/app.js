// Utilidades globales para formateo de moneda COP, alertas y modales interactivos

function formatCOP(valor) {
    const num = Math.round(Number(valor) || 0);
    const signo = num < 0 ? "- " : "";
    return signo + "$ " + Math.abs(num).toLocaleString("es-CO");
}

function abrirModal(idModal) {
    const el = document.getElementById(idModal);
    if (el) {
        el.classList.remove("hidden");
        el.classList.add("flex");
    }
}

function cerrarModal(idModal) {
    const el = document.getElementById(idModal);
    if (el) {
        el.classList.add("hidden");
        el.classList.remove("flex");
    }
}

// Abrir modal global de Abono Rápido con validación instantánea de deuda máxima
function abrirModalAbono(ventaId, numeroFactura, clienteNombre, saldoPendiente) {
    const saldo = Math.round(Number(saldoPendiente) || 0);
    document.getElementById("abono_venta_id").value = ventaId;
    document.getElementById("abono_factura_label").textContent = numeroFactura;
    document.getElementById("abono_cliente_label").textContent = clienteNombre;
    document.getElementById("abono_saldo_max").value = saldo;
    document.getElementById("abono_saldo_display").textContent = formatCOP(saldo);

    // Por defecto pre-llenar todo en efectivo para cobrar con 1 clic
    const inputEfec = document.getElementById("abono_efectivo");
    const inputTrans = document.getElementById("abono_transferencia");
    inputEfec.value = saldo;
    inputTrans.value = 0;

    actualizarCalculoAbono();
    abrirModal("modalAbonoGlobal");
}

function seleccionarModoAbono(modo) {
    const saldoMax = Number(document.getElementById("abono_saldo_max").value) || 0;
    const inputEfec = document.getElementById("abono_efectivo");
    const inputTrans = document.getElementById("abono_transferencia");

    if (modo === "EFECTIVO_TOTAL") {
        inputEfec.value = saldoMax;
        inputTrans.value = 0;
    } else if (modo === "TRANSFERENCIA_TOTAL") {
        inputEfec.value = 0;
        inputTrans.value = saldoMax;
    } else if (modo === "MITAD_Y_MITAD") {
        const mitad = Math.floor(saldoMax / 2);
        inputEfec.value = mitad;
        inputTrans.value = saldoMax - mitad;
    } else if (modo === "LIMPIAR") {
        inputEfec.value = 0;
        inputTrans.value = 0;
        inputEfec.focus();
    }
    actualizarCalculoAbono();
}

function actualizarCalculoAbono() {
    const saldoMax = Number(document.getElementById("abono_saldo_max").value) || 0;
    const efec = Math.max(Number(document.getElementById("abono_efectivo").value) || 0, 0);
    const trans = Math.max(Number(document.getElementById("abono_transferencia").value) || 0, 0);
    const totalAbonar = efec + trans;
    const restante = saldoMax - totalAbonar;

    const totalEl = document.getElementById("abono_total_preview");
    const restanteEl = document.getElementById("abono_restante_preview");
    const alertaEl = document.getElementById("abono_error_msg");
    const btnSubmit = document.getElementById("btn_confirmar_abono");

    totalEl.textContent = formatCOP(totalAbonar);

    if (totalAbonar > saldoMax) {
        restanteEl.textContent = "Excede la deuda por " + formatCOP(totalAbonar - saldoMax);
        restanteEl.className = "font-extrabold text-rose-600";
        alertaEl.classList.remove("hidden");
        alertaEl.textContent = "⚠️ No puedes registrar un pago mayor a la deuda pendiente (" + formatCOP(saldoMax) + ").";
        btnSubmit.disabled = true;
        btnSubmit.classList.add("opacity-50", "cursor-not-allowed");
    } else if (totalAbonar <= 0) {
        restanteEl.textContent = formatCOP(saldoMax);
        restanteEl.className = "font-bold text-amber-600";
        alertaEl.classList.add("hidden");
        btnSubmit.disabled = true;
        btnSubmit.classList.add("opacity-50", "cursor-not-allowed");
    } else {
        alertaEl.classList.add("hidden");
        btnSubmit.disabled = false;
        btnSubmit.classList.remove("opacity-50", "cursor-not-allowed");
        if (restante === 0) {
            restanteEl.textContent = "$ 0 (¡Queda PAGADA!)";
            restanteEl.className = "font-extrabold text-emerald-600";
        } else {
            restanteEl.textContent = formatCOP(restante) + " (Queda con saldo parcial)";
            restanteEl.className = "font-bold text-amber-600";
        }
    }
}

// Auto-ocultar notificaciones flash después de 6 segundos
document.addEventListener("DOMContentLoaded", () => {
    const flashBanner = document.getElementById("flash-banner");
    if (flashBanner) {
        setTimeout(() => {
            flashBanner.style.transition = "opacity 0.5s ease";
            flashBanner.style.opacity = "0";
            setTimeout(() => flashBanner.remove(), 500);
        }, 6500);
    }
});
