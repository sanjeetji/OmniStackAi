/** Mock Logistics and Courier provider for Bazaar. */

export interface CourierInfo {
  id: string;
  name: string;
  code: string;
  standardDays: number;
}

export const SUPPORTED_COURIERS: CourierInfo[] = [
  { id: "delhivery", name: "Delhivery Surface & Express", code: "DLHV", standardDays: 3 },
  { id: "bluedart", name: "BlueDart Apex", code: "BLDT", standardDays: 2 },
  { id: "shadowfax", name: "Shadowfax Hyperlocal", code: "SHFX", standardDays: 1 },
  { id: "ekart", name: "Ekart Logistics", code: "EKRT", standardDays: 3 },
];

export class MockLogisticsProvider {
  getCouriers(): CourierInfo[] {
    return SUPPORTED_COURIERS;
  }

  generateTrackingNumber(courierId: string = "delhivery"): {
    courierName: string;
    trackingNumber: string;
  } {
    const courier =
      SUPPORTED_COURIERS.find((c) => c.id === courierId) || SUPPORTED_COURIERS[0];
    const prefix = courier.code;
    const randomDigits = Math.floor(100000000 + Math.random() * 900000000);
    return {
      courierName: courier.name,
      trackingNumber: `${prefix}${randomDigits}`,
    };
  }

  getSimulatedEvents(
    status: string,
    city: string
  ): Array<{ status: string; location: string; message: string }> {
    switch (status) {
      case "placed":
        return [
          {
            status: "placed",
            location: "Seller Hub",
            message: "Order placed and assigned to seller warehouse",
          },
        ];
      case "accepted":
        return [
          {
            status: "placed",
            location: "Seller Hub",
            message: "Order placed and assigned to seller warehouse",
          },
          {
            status: "accepted",
            location: "Seller Hub",
            message: "Seller has confirmed order and started preparation",
          },
        ];
      case "packed":
        return [
          {
            status: "accepted",
            location: "Seller Hub",
            message: "Seller has confirmed order and started preparation",
          },
          {
            status: "packed",
            location: "Seller Warehouse",
            message: "Package sealed with tamper-proof packaging and shipping label affixed",
          },
        ];
      case "shipped":
        return [
          {
            status: "packed",
            location: "Seller Warehouse",
            message: "Package sealed with tamper-proof packaging and shipping label affixed",
          },
          {
            status: "shipped",
            location: "Sorting Hub",
            message: `Picked up by courier and in transit towards ${city}`,
          },
        ];
      case "delivered":
        return [
          {
            status: "shipped",
            location: "Sorting Hub",
            message: `In transit towards destination facility`,
          },
          {
            status: "out_for_delivery",
            location: `${city} Delivery Center`,
            message: "Package is out for delivery with courier associate",
          },
          {
            status: "delivered",
            location: city,
            message: "Package delivered and signed by recipient",
          },
        ];
      case "cancelled":
        return [
          {
            status: "cancelled",
            location: "Origin Hub",
            message: "Shipment cancelled. Goods returned to available stock",
          },
        ];
      default:
        return [
          {
            status,
            location: "Logistics Network",
            message: `Shipment status updated to ${status}`,
          },
        ];
    }
  }
}

export const logisticsProvider = new MockLogisticsProvider();
