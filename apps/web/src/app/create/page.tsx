import { Suspense } from "react";
import { BillingToast } from "@/components/billing-toast";
import { CreateWizard } from "@/components/create-wizard";

export default function CreatePage() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <Suspense>
        <BillingToast />
      </Suspense>
      <h1 className="mb-8 text-3xl font-semibold tracking-tight">Yeni şarkı</h1>
      <CreateWizard />
    </div>
  );
}
