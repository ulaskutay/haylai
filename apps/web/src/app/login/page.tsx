import { Suspense } from "react";
import { LoginForm } from "@/components/login-form";

export default function LoginPage() {
  return (
    <div className="flex min-h-[70vh] items-center px-4">
      <Suspense>
        <LoginForm />
      </Suspense>
    </div>
  );
}
