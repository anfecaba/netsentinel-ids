<template>
  <section
    class="rounded-xl border border-amber-500/30 bg-amber-500/[0.06] px-4 py-3 text-sm"
    aria-label="Aviso legal del laboratorio"
  >
    <div class="flex flex-col gap-2 sm:flex-row sm:items-start sm:gap-3">
      <span class="mt-0.5 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-md border border-amber-500/40 bg-amber-500/10 text-amber-300">
        <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v4m0 4h.01M10.3 3.9L2.6 17a2 2 0 001.7 3h15.4a2 2 0 001.7-3L13.7 3.9a2 2 0 00-3.4 0z" />
        </svg>
      </span>
      <div class="space-y-1">
        <p class="font-semibold text-amber-200">
          Solo laboratorio: captura pasiva únicamente en redes propias o con autorización escrita.
        </p>
        <p class="text-xs leading-relaxed text-amber-100/70">
          Interceptar datos de terceros puede constituir el delito de interceptación de datos
          informáticos (Ley 1273 de 2009, art. 269C, Colombia). El backend exige
          <code class="rounded bg-background/60 px-1 py-0.5 text-[11px]">--i-have-authorization</code>
          para capturar tráfico real.
        </p>
      </div>
    </div>

    <details class="mt-2 text-xs text-amber-100/70">
      <summary class="cursor-pointer select-none font-medium text-amber-200/90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-400">
        Alcance y límites de esta demostración
      </summary>
      <ul class="mt-2 grid gap-1 pl-5 sm:grid-cols-2">
        <li class="list-disc">Sin ARP spoofing ni suplantación de gateway.</li>
        <li class="list-disc">Sin SSL stripping ni ruptura de TLS.</li>
        <li class="list-disc">Sin inyección de paquetes.</li>
        <li class="list-disc">Credenciales solo en memoria; nunca en disco por defecto.</li>
      </ul>
    </details>
  </section>
</template>
