"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@bazaar/shared";
import type { UserAddress } from "@bazaar/shared";

const INITIAL_ADDRESSES: UserAddress[] = [
  {
    id: "addr-001",
    user_id: "u-shopper-001",
    label: "Home (Indiranagar)",
    recipient_name: "Priya Sharma",
    phone: "+91 98765 43210",
    street: "Flat 402, Lotus Granduer, 12th Main Road, Indiranagar",
    city: "Bengaluru",
    state: "Karnataka",
    postal_code: "560038",
    country: "India",
    is_default: true,
  },
  {
    id: "addr-002",
    user_id: "u-shopper-001",
    label: "Work (Whitefield Tech Hub)",
    recipient_name: "Priya Sharma",
    phone: "+91 98765 43210",
    street: "Level 6, Block B, Brigade Tech Park, ITPL Main Rd",
    city: "Bengaluru",
    state: "Karnataka",
    postal_code: "560066",
    country: "India",
    is_default: false,
  },
];

export default function AddressesPage() {
  const [addresses, setAddresses] = useState<UserAddress[]>(INITIAL_ADDRESSES);
  const [showAddModal, setShowAddModal] = useState(false);
  const [formData, setFormData] = useState({
    label: "Home",
    recipientName: "Priya Sharma",
    phone: "+91 98765 43210",
    street: "",
    city: "",
    state: "",
    postalCode: "",
    country: "India",
    isDefault: false,
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function loadAddresses() {
      try {
        const res = await api.getAddresses();
        if (Array.isArray(res) && res.length > 0) {
          setAddresses(res);
        } else if ((res as any)?.addresses && (res as any).addresses.length > 0) {
          setAddresses((res as any).addresses);
        }
      } catch {
        // Fallback to demo addresses
        setAddresses(INITIAL_ADDRESSES);
      }
    }
    loadAddresses();
  }, []);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    try {
      setLoading(true);
      const res = await api.addAddress(formData);
      if (res && (res as any).id) {
        setAddresses([res, ...addresses]);
      } else {
        const localAddr: UserAddress = {
          id: `addr-${Date.now()}`,
          user_id: "u-shopper-001",
          label: formData.label,
          recipient_name: formData.recipientName,
          phone: formData.phone,
          street: formData.street,
          city: formData.city,
          state: formData.state,
          postal_code: formData.postalCode,
          country: formData.country,
          is_default: formData.isDefault,
        };
        setAddresses([localAddr, ...addresses]);
      }
      setShowAddModal(false);
      setFormData({
        label: "Home",
        recipientName: "Priya Sharma",
        phone: "+91 98765 43210",
        street: "",
        city: "",
        state: "",
        postalCode: "",
        country: "India",
        isDefault: false,
      });
    } catch {
      const localAddr: UserAddress = {
        id: `addr-${Date.now()}`,
        user_id: "u-shopper-001",
        label: formData.label,
        recipient_name: formData.recipientName,
        phone: formData.phone,
        street: formData.street,
        city: formData.city,
        state: formData.state,
        postal_code: formData.postalCode,
        country: formData.country,
        is_default: formData.isDefault,
      };
      setAddresses([localAddr, ...addresses]);
      setShowAddModal(false);
    } finally {
      setLoading(false);
    }
  }

  function handleSetDefault(id: string) {
    setAddresses(
      addresses.map((a) => ({
        ...a,
        is_default: a.id === id,
      }))
    );
  }

  function handleDelete(id: string) {
    setAddresses(addresses.filter((a) => a.id !== id));
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-sm text-stone-500 mb-6">
        <Link href="/account" className="hover:text-amber-800">
          My Account
        </Link>
        <span>&rsaquo;</span>
        <span className="font-semibold text-stone-800">Address Book</span>
      </nav>

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-serif font-bold text-stone-900">Saved Addresses</h1>
          <p className="text-stone-600 text-sm mt-1">
            Manage your verified shipping locations for seamless multi-vendor artisan dispatch.
          </p>
        </div>

        <button
          onClick={() => setShowAddModal(true)}
          className="px-5 py-2.5 bg-amber-700 hover:bg-amber-800 text-white rounded-xl text-sm font-semibold transition self-start sm:self-auto flex items-center gap-2 shadow-sm"
        >
          <span>+</span>
          <span>Add New Address</span>
        </button>
      </div>

      {/* Address Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {addresses.map((addr) => (
          <div
            key={addr.id}
            className={`p-6 rounded-2xl border transition relative flex flex-col justify-between ${
              addr.is_default
                ? "bg-amber-50/40 border-amber-300 ring-1 ring-amber-300 shadow-sm"
                : "bg-white border-stone-200 hover:border-stone-300 shadow-sm"
            }`}
          >
            <div>
              <div className="flex items-center justify-between gap-2 mb-3">
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-stone-100 text-stone-700">
                  {addr.label || "Address"}
                </span>
                {addr.is_default && (
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-700 text-white">
                    Default Shipping
                  </span>
                )}
              </div>

              <h3 className="text-base font-bold text-stone-900">{addr.recipient_name}</h3>
              <p className="text-sm text-stone-600 mt-1">{addr.street}</p>
              <p className="text-sm text-stone-600">
                {addr.city}, {addr.state} - {addr.postal_code}
              </p>
              <p className="text-xs text-stone-500 mt-2 font-mono">Mobile: {addr.phone}</p>
            </div>

            <div className="mt-6 pt-4 border-t border-stone-100 flex items-center justify-between text-xs">
              {!addr.is_default ? (
                <button
                  onClick={() => handleSetDefault(addr.id)}
                  className="text-amber-800 hover:text-amber-900 font-semibold"
                >
                  Set as Default
                </button>
              ) : (
                <span className="text-emerald-700 font-medium">✓ Default Address</span>
              )}

              <button
                onClick={() => handleDelete(addr.id)}
                className="text-red-600 hover:text-red-800 font-medium"
              >
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Add Address Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl max-h-[90vh] overflow-y-auto">
            <h3 className="text-xl font-serif font-bold text-stone-900 mb-2">
              Add New Delivery Destination
            </h3>
            <p className="text-xs text-stone-500 mb-6">
              Ensure accurate pincode and mobile number for carrier delivery updates.
            </p>

            <form onSubmit={handleAdd} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-stone-700 uppercase mb-1">
                    Label
                  </label>
                  <input
                    type="text"
                    value={formData.label}
                    onChange={(e) => setFormData({ ...formData, label: e.target.value })}
                    placeholder="Home / Work / Studio"
                    className="w-full text-sm rounded-lg border border-stone-300 p-2.5"
                    required
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-stone-700 uppercase mb-1">
                    Recipient Full Name
                  </label>
                  <input
                    type="text"
                    value={formData.recipientName}
                    onChange={(e) => setFormData({ ...formData, recipientName: e.target.value })}
                    className="w-full text-sm rounded-lg border border-stone-300 p-2.5"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-stone-700 uppercase mb-1">
                  Contact Mobile Number
                </label>
                <input
                  type="text"
                  value={formData.phone}
                  onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  placeholder="+91 98765 43210"
                  className="w-full text-sm rounded-lg border border-stone-300 p-2.5 font-mono"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-stone-700 uppercase mb-1">
                  Street Address & Flat / House No
                </label>
                <textarea
                  value={formData.street}
                  onChange={(e) => setFormData({ ...formData, street: e.target.value })}
                  rows={2}
                  placeholder="e.g. 402 Lotus Granduer, 12th Main Road, Indiranagar"
                  className="w-full text-sm rounded-lg border border-stone-300 p-2.5"
                  required
                />
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-stone-700 uppercase mb-1">
                    City
                  </label>
                  <input
                    type="text"
                    value={formData.city}
                    onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                    placeholder="Bengaluru"
                    className="w-full text-sm rounded-lg border border-stone-300 p-2.5"
                    required
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-stone-700 uppercase mb-1">
                    State
                  </label>
                  <input
                    type="text"
                    value={formData.state}
                    onChange={(e) => setFormData({ ...formData, state: e.target.value })}
                    placeholder="Karnataka"
                    className="w-full text-sm rounded-lg border border-stone-300 p-2.5"
                    required
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-stone-700 uppercase mb-1">
                    PIN Code
                  </label>
                  <input
                    type="text"
                    value={formData.postalCode}
                    onChange={(e) => setFormData({ ...formData, postalCode: e.target.value })}
                    placeholder="560038"
                    className="w-full text-sm rounded-lg border border-stone-300 p-2.5 font-mono"
                    required
                  />
                </div>
              </div>

              <div className="flex items-center gap-2 pt-2">
                <input
                  type="checkbox"
                  id="isDefaultCheck"
                  checked={formData.isDefault}
                  onChange={(e) => setFormData({ ...formData, isDefault: e.target.checked })}
                  className="w-4 h-4 text-amber-700 rounded border-stone-300"
                />
                <label htmlFor="isDefaultCheck" className="text-xs text-stone-700 font-medium">
                  Set as default shipping address
                </label>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-stone-100">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 text-stone-600 text-xs font-semibold hover:bg-stone-100 rounded-xl"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-6 py-2 bg-amber-700 hover:bg-amber-800 text-white rounded-xl text-xs font-semibold disabled:opacity-50 transition"
                >
                  {loading ? "Saving..." : "Save Address"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
