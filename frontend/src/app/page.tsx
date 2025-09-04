/**
 * 首頁 - 重定向到儀表板
 */

import { redirect } from 'next/navigation';

export default function Home() {
  redirect('/dashboard');
}
