from langchain_core.tools import tool

# ==========================================================
# MOCK DATA – Cơ sở dữ liệu giả lập hệ thống du lịch
# ==========================================================

FLIGHTS_DB = {
    ("Hà Nội", "Đà Nẵng"): [
        {"airline": "Vietnam Airlines", "departure": "06:00", "arrival": "07:20", "price": 1450000, "class": "economy"},
        {"airline": "VietJet Air", "departure": "09:00", "arrival": "10:20", "price": 950000, "class": "economy"},
        {"airline": "Vietnam Airlines", "departure": "14:00", "arrival": "15:20", "price": 2800000, "class": "business"},
    ],
    ("TP.HCM", "Đà Nẵng"): [
        {"airline": "Bamboo Airways", "departure": "08:00", "arrival": "09:20", "price": 1200000, "class": "economy"},
        {"airline": "Vietnam Airlines", "departure": "13:00", "arrival": "14:20", "price": 1600000, "class": "economy"},
    ],
    ("Hà Nội", "Phú Quốc"): [
        {"airline": "Vietnam Airlines", "departure": "07:00", "arrival": "09:10", "price": 2100000, "class": "economy"},
        {"airline": "VietJet Air", "departure": "11:00", "arrival": "13:10", "price": 1500000, "class": "economy"},
    ]
}

HOTELS_DB = {
    "Đà Nẵng": [
        {"name": "Green House", "stars": 3, "price_per_night": 600000, "location": "Gần biển My Khê"},
        {"name": "InterContinental", "stars": 5, "price_per_night": 1800000, "location": "Bán đảo Sơn Trà"},
        {"name": "Diamond Hotel", "stars": 4, "price_per_night": 1100000, "location": "Trung tâm thành phố"},
    ],
    "Phú Quốc": [
        {"name": "Vinpearl Resort", "stars": 5, "price_per_night": 2500000, "location": "Bắc Đảo"},
        {"name": "Sunset Beach", "stars": 3, "price_per_night": 800000, "location": "Thị trấn Dương Đông"},
    ]
}

# ==========================================================
# DEFINING TOOLS
# ==========================================================

@tool
def search_flights(departure: str, destination: str) -> dict | str:
    """
    Tra cứu thông tin chuyến bay dựa trên điểm đi và điểm đến.
    - Hỗ trợ tìm chiều xuôi (Hà Nội -> Đà Nẵng)
    - Nếu không có, tự động thử chiều ngược (Đà Nẵng -> Hà Nội)
    - Trả về danh sách các chuyến bay sắp xếp theo giá tăng dần
    """
    # Chuẩn hóa input để tránh lỗi hoa thường
    dep = departure.strip()
    dest = destination.strip()
    
    # Tìm chiều xuôi
    flights = FLIGHTS_DB.get((dep, dest))
    if flights:
        # Sắp xếp theo giá tăng dần
        sorted_flights = sorted(flights, key=lambda x: x["price"])
        return {
            "route": f"{dep} → {dest}",
            "direction": "Chiều xuôi",
            "flights": sorted_flights
        }
    
    # Nếu không tìm được, thử chiều ngược
    reverse_flights = FLIGHTS_DB.get((dest, dep))
    if reverse_flights:
        sorted_flights = sorted(reverse_flights, key=lambda x: x["price"])
        return {
            "route": f"{dest} → {dep}",
            "direction": "Chiều ngược",
            "flights": sorted_flights,
            "note": "⚠️ Không có chuyến bay trực tiếp từ {dep} đến {dest}, nhưng có chiều ngược. Bạn có quan tâm không?"
        }
    
    return f"Rất tiếc, TravelBuddy hiện chưa có chuyến bay trực tiếp giữa {dep} và {dest}."

@tool
def search_hotels(city: str, budget: int, nights: int = 1) -> dict | str:
    """
    Tìm kiếm & lọc khách sạn tại một thành phố cụ thể dựa trên:
    - Ngân sách còn lại của khách hàng
    - Số đêm ở (tínhính tổng giá phòng)
    
    Sắp xếp theo chiến lược:
    1. Khách sạn phù hợp ngân sách (giá_phòng × đêm ≤ ngân sách)
    2. Ưu tiên sao cao hơn (chất lượng tốt)
    3. Giá thấp hơn trong cùng mức sao (tiết kiệm)
    """
    city_name = city.strip()
    hotels = HOTELS_DB.get(city_name)
    
    if not hotels:
        return f"Hiện tại TravelBuddy chưa có dữ liệu khách sạn tại {city_name}."
    
    # Lọc khách sạn phù hợp ngân sách
    affordable_hotels = [
        h for h in hotels 
        if (h["price_per_night"] * nights) <= budget
    ]
    
    if not affordable_hotels:
        # Trả về thông tin chi tiết về lý do không tìm được
        min_price = min(h["price_per_night"] for h in hotels)
        return {
            "status": "not_found",
            "city": city_name,
            "budget": budget,
            "nights": nights,
            "total_budget_needed": min_price * nights,
            "message": f"❌ Không tìm thấy khách sạn nào tại {city_name} phù hợp với ngân sách {budget:,} VNĐ ({nights} đêm).\n"
                      f"💡 Khách sạn rẻ nhất cần {min_price * nights:,} VNĐ. Bạn muốn tăng ngân sách hoặc giảm số đêm không?"
        }
    
    # Sắp xếp: sao cao → giá thấp
    sorted_hotels = sorted(
        affordable_hotels,
        key=lambda x: (-x["stars"], x["price_per_night"])  # Sao cao trước, rồi giá thấp
    )
    
    # Tính tổng giá cho các đêm
    result_hotels = []
    for hotel in sorted_hotels:
        total_cost = hotel["price_per_night"] * nights
        result_hotels.append({
            **hotel,
            "total_cost": total_cost,
            "description": f"⭐×{hotel['stars']} - {hotel['name']} ({hotel['location']}) | {hotel['price_per_night']:,} VNĐ/đêm → {total_cost:,} VNĐ ({nights} đêm)"
        })
    
    return {
        "status": "success",
        "city": city_name,
        "budget_available": budget,
        "nights": nights,
        "count": len(result_hotels),
        "hotels": result_hotels
    }

@tool
def calculate_budget(total_budget: int | str, expenses: list | str) -> dict:
    """
    Tính toán chi tiết ngân sách:
    - Parse input (int, string với format: "1,000,000" hoặc "1000000")
    - Xử lý lỗi format (invalid input)
    - Tính toán thực sự: tổng chi phí, còn lại, % sử dụng
    - Cảnh báo nếu vượt ngân sách hoặc ngân sách còn quá ít
    
    Parameters:
    - total_budget: int hoặc string (ví dụ: "10000000" hoặc "10,000,000")
    - expenses: list of int/str hoặc string phân tách bằng dấu phẩy
    """
    try:
        # Parse total_budget
        if isinstance(total_budget, str):
            # Loại bỏ dấu phẩy, khoảng trắng
            total_budget = int(total_budget.replace(",", "").replace(".", "").strip())
        
        total_budget = int(total_budget)
        
        if total_budget <= 0:
            return {
                "status": "error",
                "message": "❌ Ngân sách phải là số dương (> 0)."
            }
        
        # Parse expenses
        if isinstance(expenses, str):
            # Có thể là: "1000000, 2000000, 500000" hoặc "1000000 2000000 500000"
            expenses = [
                int(e.replace(",", "").replace(".", "").strip())
                for e in expenses.replace(";", ",").split(",")
                if e.strip()
            ]
        
        if not isinstance(expenses, list):
            expenses = [expenses]
        
        expenses = [int(e) for e in expenses if e]
        
        # Tính toán
        total_expenses = sum(expenses)
        remaining_budget = total_budget - total_expenses
        percentage_used = (total_expenses / total_budget) * 100 if total_budget > 0 else 0
        
        # Xác định trạng thái
        status = "success"
        warnings = []
        
        if remaining_budget < 0:
            status = "warning"
            warnings.append(f"⚠️ VƯỢT NGÂN SÁCH: Thiếu {abs(remaining_budget):,} VNĐ")
        
        if remaining_budget > 0 and remaining_budget <= (total_budget * 0.05):  # < 5%
            warnings.append(f"⚠️ Ngân sách còn rất ít (< 5%): {remaining_budget:,} VNĐ")
        
        if remaining_budget > (total_budget * 0.7):  # > 70%
            warnings.append(f"✅ Bạn vẫn có ngân sách dư: {remaining_budget:,} VNĐ. Tốt lắm!")
        
        return {
            "status": status,
            "total_budget": total_budget,
            "total_expenses": total_expenses,
            "breakdown": {
                "items": expenses,
                "count": len(expenses)
            },
            "remaining_budget": remaining_budget,
            "percentage_used": round(percentage_used, 1),
            "percentage_remaining": round(100 - percentage_used, 1),
            "status_message": "Trong tầm kiểm soát ✅" if remaining_budget >= 0 else "Vượt ngân sách ❌",
            "warnings": warnings,
            "summary": f"💰 Tổng chi phí: {total_expenses:,} VNĐ | Còn lại: {remaining_budget:,} VNĐ ({round(100 - percentage_used, 1)}%)"
        }
    
    except ValueError as e:
        return {
            "status": "error",
            "message": f"❌ Lỗi định dạng dữ liệu: {str(e)}\n"
                      f"💡 Vui lòng nhập:\n"
                      f"   - total_budget: số nguyên (ví dụ: 10000000 hoặc '10,000,000')\n"
                      f"   - expenses: danh sách số (ví dụ: [1000000, 500000] hoặc '1000000, 500000')"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"❌ Lỗi không xác định: {str(e)}"
        }