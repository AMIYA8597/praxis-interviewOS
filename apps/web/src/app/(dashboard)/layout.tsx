"use client";

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabase';
import { LayoutDashboard, Users, Briefcase, Target, Activity, Settings, LogOut, Loader2 } from 'lucide-react';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    const checkAuth = async () => {
      // Allow mock mode if no Supabase URL is set
      if (!process.env.NEXT_PUBLIC_SUPABASE_URL) {
        setIsLoading(false);
        return;
      }
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        router.push('/auth');
      } else {
        setIsLoading(false);
      }
    };
    checkAuth();

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      if (!session && process.env.NEXT_PUBLIC_SUPABASE_URL) {
        router.push('/auth');
      }
    });

    return () => subscription.unsubscribe();
  }, [router]);

  const handleSignOut = async () => {
    if (process.env.NEXT_PUBLIC_SUPABASE_URL) {
      await supabase.auth.signOut();
    } else {
      router.push('/auth');
    }
  };

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-950 text-gray-400">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  const navItems = [
    { name: 'Analytics', href: '/analytics', icon: Activity },
    { name: 'Candidates', href: '/candidates', icon: Users },
    { name: 'Study Workbench', href: '/study', icon: Target },
    { name: 'Job Matches', href: '/platform/tracker', icon: Briefcase },
    { name: 'Settings', href: '/settings/providers', icon: Settings },
  ];

  return (
    <div className="flex h-screen bg-gray-950 text-gray-100 font-sans selection:bg-indigo-500/30">
      <aside className="w-64 border-r border-gray-800 bg-gray-900/50 flex flex-col">
        <div className="h-16 flex items-center px-6 border-b border-gray-800">
          <span className="text-lg font-bold tracking-widest uppercase text-gray-200">PRAXIS</span>
        </div>
        
        <nav className="flex-1 overflow-y-auto py-6 px-3 space-y-1">
          {navItems.map((item) => {
            const isActive = pathname.startsWith(item.href);
            return (
              <Link
                key={item.name}
                href={item.href}
                className={`flex items-center space-x-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  isActive 
                    ? 'bg-gray-800 text-white' 
                    : 'text-gray-400 hover:bg-gray-800/50 hover:text-gray-200'
                }`}
              >
                <item.icon className="h-4 w-4" />
                <span>{item.name}</span>
              </Link>
            );
          })}
        </nav>

        <div className="p-4 border-t border-gray-800">
          <button
            onClick={handleSignOut}
            className="flex items-center space-x-3 w-full px-3 py-2 rounded-md text-sm font-medium text-gray-400 hover:bg-gray-800 hover:text-white transition-colors"
          >
            <LogOut className="h-4 w-4" />
            <span>Sign Out</span>
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-y-auto">
        {children}
      </main>
    </div>
  );
}
