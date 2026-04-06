import { Suspense } from "react";
import { MyProfilePage } from "@/components/profile/my-profile-page";

export default function ProfileMePage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <MyProfilePage />
    </Suspense>
  );
}
